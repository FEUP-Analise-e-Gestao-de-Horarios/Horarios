import { WEEKDAYS } from "@/utils/weekdays";

/** Day order used when bit-packing the day filter into the URL. */
export const SCHEDULE_VIEW_DAYS = WEEKDAYS;

export type ScheduleViewSelection = {
  degreeId: string;
  ano: string;
  ucs: string[];
  turmas: string[];
  dias: string[];
  semanas: string[];
};

export type ScheduleViewOrders = {
  ucOrder: string[];
  turmaOrder: string[];
  weekOrder: string[];
};

export type ScheduleViewParts = {
  degreeKey?: string;
  year?: string;
  bytes?: Uint8Array;
};

export function degreeKey(degreeId: string): string {
  return degreeId
    .replace(/[^A-Za-z0-9]/g, "")
    .slice(-4)
    .toLowerCase();
}

function setBit(bytes: Uint8Array, bitIndex: number) {
  const byteIndex = bitIndex >> 3;
  const bit = bitIndex & 7;
  if (byteIndex >= bytes.length) return;
  bytes[byteIndex] = (bytes[byteIndex] ?? 0) | (1 << bit);
}

function getBit(bytes: Uint8Array, bitIndex: number): boolean {
  const byteIndex = bitIndex >> 3;
  const bit = bitIndex & 7;
  if (byteIndex >= bytes.length) return false;
  return ((bytes[byteIndex] ?? 0) & (1 << bit)) !== 0;
}

function packSections(sections: { values: string[]; ref: string[] }[]): Uint8Array {
  const totalBits = sections.reduce((sum, section) => sum + section.ref.length, 0);
  if (totalBits === 0) return new Uint8Array();
  const bytes = new Uint8Array(Math.ceil(totalBits / 8));

  // Encoding convention:
  //   - empty selection (`values.length === 0`)  → all bits zero, decoded as
  //     "no filter active";
  //   - any other selection (including an explicit pick of every reference
  //     value) → bit per selected value.
  //
  // The previous version also encoded `[]` as all-bits-set, which was
  // indistinguishable from an explicit pick of all reference values once
  // round-tripped, so the explicit selection was silently collapsed to
  // "no filter" on the consumer side.
  let offset = 0;
  for (const section of sections) {
    if (section.values.length > 0) {
      const selected = new Set(section.values);
      section.ref.forEach((value, index) => {
        if (selected.has(value)) setBit(bytes, offset + index);
      });
    }
    offset += section.ref.length;
  }

  return bytes;
}

export type UnpackedSection = {
  /** Reference values whose bit was set. Empty means "no filter active". */
  values: string[];
  /** True iff *every* reference value's bit was set (explicit pick of all). */
  isAll: boolean;
};

export function unpackSections(
  bytes: Uint8Array,
  sections: { ref: string[] }[],
): UnpackedSection[] {
  const result: UnpackedSection[] = [];
  let offset = 0;
  for (const section of sections) {
    const values: string[] = [];
    let allSet = section.ref.length > 0;
    for (let i = 0; i < section.ref.length; i++) {
      const set = getBit(bytes, offset + i);
      const value = section.ref[i];
      if (set) {
        if (value !== undefined) values.push(value);
      } else {
        allSet = false;
      }
    }
    // `allSet` is meaningful only when at least one bit fired; an all-zeros
    // section means "no filter active", which is not the same as "explicit
    // pick of every reference value".
    result.push({ values, isAll: allSet && values.length > 0 });
    offset += section.ref.length;
  }
  return result;
}

const BASE64_URL_REPLACE_OUT: Record<string, string> = { "+": "-", "/": "_" };
const BASE64_URL_REPLACE_IN: Record<string, string> = { "-": "+", _: "/" };

function bytesToBase64Url(bytes: Uint8Array): string {
  if (bytes.length === 0) return "";
  let binary = "";
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i] ?? 0);
  return btoa(binary)
    .replace(/[+/]/g, (ch) => BASE64_URL_REPLACE_OUT[ch] ?? ch)
    .replace(/=+$/, "");
}

function base64UrlToBytes(text: string): Uint8Array {
  if (!text) return new Uint8Array();
  const standard = text.replace(/[-_]/g, (ch) => BASE64_URL_REPLACE_IN[ch] ?? ch);
  const padLen = (4 - (standard.length % 4)) % 4;
  const padded = standard + "=".repeat(padLen);
  let binary: string;
  try {
    binary = atob(padded);
  } catch {
    return new Uint8Array();
  }
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

export function encodeScheduleView(
  selection: ScheduleViewSelection,
  orders: ScheduleViewOrders,
): string {
  if (!selection.degreeId) return "";
  const key = degreeKey(selection.degreeId);
  if (!key) return "";

  const segments: string[] = [key];
  if (selection.ano) segments.push(selection.ano);

  // The dias filter is initialised as "every weekday selected" — the user can
  // toggle individual days off but the UI starts fully checked. That state is
  // observationally identical to "no day filter active", so collapse it to an
  // empty selection here so the canonical default URL stays compact.
  const normalizedDias = selection.dias.length === SCHEDULE_VIEW_DAYS.length ? [] : selection.dias;

  const sections = [
    { values: selection.ucs, ref: orders.ucOrder },
    { values: selection.turmas, ref: orders.turmaOrder },
    { values: normalizedDias, ref: [...SCHEDULE_VIEW_DAYS] },
    { values: selection.semanas, ref: orders.weekOrder },
  ];

  // Skip the bytes segment only when every section is unfiltered (empty
  // selection). An explicit pick of every reference value, by contrast, is
  // preserved through the bit pattern so the consumer can round-trip it
  // distinctly from "no filter".
  const everythingDefault = sections.every((section) => section.values.length === 0);
  if (!everythingDefault && selection.ano) {
    const bytes = packSections(sections);
    segments.push(bytesToBase64Url(bytes));
  }

  return segments.join(":");
}

export function parseScheduleView(view: string | null | undefined): ScheduleViewParts {
  if (!view) return {};
  const parts = view.split(":");
  const result: ScheduleViewParts = {};
  if (parts[0]) result.degreeKey = parts[0];
  if (parts[1]) result.year = parts[1];
  if (parts[2]) result.bytes = base64UrlToBytes(parts[2]);
  return result;
}
