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

  let offset = 0;
  for (const section of sections) {
    const isAll = section.values.length === 0 || section.values.length === section.ref.length;
    if (isAll) {
      for (let i = 0; i < section.ref.length; i++) setBit(bytes, offset + i);
    } else {
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
  values: string[];
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
    result.push({ values, isAll: allSet });
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

function isAllSelected(values: string[], ref: string[]): boolean {
  if (ref.length === 0) return true;
  return values.length === 0 || values.length === ref.length;
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

  const sections = [
    { values: selection.ucs, ref: orders.ucOrder },
    { values: selection.turmas, ref: orders.turmaOrder },
    { values: selection.dias, ref: [...SCHEDULE_VIEW_DAYS] },
    { values: selection.semanas, ref: orders.weekOrder },
  ];

  const everythingAll = sections.every((section) => isAllSelected(section.values, section.ref));
  if (!everythingAll && selection.ano) {
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
