import { describe, expect, it } from "vitest";
import {
  SCHEDULE_VIEW_DAYS,
  degreeKey,
  encodeScheduleView,
  parseScheduleView,
  unpackSections,
  type ScheduleViewSelection,
  type ScheduleViewOrders,
} from "./scheduleView";

describe("degreeKey", () => {
  it("keeps only alphanumerics and lowercases the last 4", () => {
    expect(degreeKey("uuid-prefix-1234")).toBe("1234");
    expect(degreeKey("uuid-prefix-ABCD")).toBe("abcd");
  });

  it("handles inputs shorter than 4 chars", () => {
    expect(degreeKey("aB")).toBe("ab");
  });

  it("returns empty for an empty input", () => {
    expect(degreeKey("")).toBe("");
  });
});

describe("encodeScheduleView", () => {
  const orders: ScheduleViewOrders = {
    ucOrder: ["UC1", "UC2", "UC3"],
    turmaOrder: ["1A", "1B"],
    weekOrder: ["w1", "w2"],
  };

  function selection(overrides: Partial<ScheduleViewSelection> = {}): ScheduleViewSelection {
    return {
      degreeId: "deg-0001",
      ano: "1",
      ucs: [],
      turmas: [],
      dias: [],
      semanas: [],
      ...overrides,
    };
  }

  it("returns an empty string when no degree is selected", () => {
    expect(encodeScheduleView(selection({ degreeId: "" }), orders)).toBe("");
  });

  it("emits just the degree key + year when every section is 'all'", () => {
    expect(encodeScheduleView(selection(), orders)).toBe("0001:1");
  });

  it("omits the bytes section when there is no year", () => {
    expect(encodeScheduleView(selection({ ano: "", ucs: ["UC1"] }), orders)).toBe("0001");
  });

  it("encodes a non-default selection with bit-packed bytes", () => {
    const view = encodeScheduleView(selection({ ucs: ["UC1"], turmas: ["1B"] }), orders);
    const parts = view.split(":");
    expect(parts[0]).toBe("0001");
    expect(parts[1]).toBe("1");
    expect(parts[2]).toBeTruthy();
  });
});

describe("parseScheduleView", () => {
  it("returns an empty object for nullish input", () => {
    expect(parseScheduleView(null)).toEqual({});
    expect(parseScheduleView(undefined)).toEqual({});
    expect(parseScheduleView("")).toEqual({});
  });

  it("extracts the degree key and year", () => {
    const parsed = parseScheduleView("abcd:2");
    expect(parsed.degreeKey).toBe("abcd");
    expect(parsed.year).toBe("2");
    expect(parsed.bytes).toBeUndefined();
  });

  it("decodes the bytes section when present", () => {
    const parsed = parseScheduleView("abcd:1:AA");
    expect(parsed.bytes).toBeInstanceOf(Uint8Array);
    expect(parsed.bytes?.length).toBeGreaterThan(0);
  });

  it("returns empty bytes (not throwing) for malformed base64", () => {
    const parsed = parseScheduleView("abcd:1:!!!!");
    expect(parsed.bytes).toBeInstanceOf(Uint8Array);
    expect(parsed.bytes?.length).toBe(0);
  });
});

describe("encode/parse round-trip", () => {
  const orders: ScheduleViewOrders = {
    ucOrder: ["UC1", "UC2", "UC3", "UC4", "UC5"],
    turmaOrder: ["1A", "1B", "2A", "2B"],
    weekOrder: ["w1", "w2", "w3"],
  };

  function roundTrip(selection: ScheduleViewSelection) {
    const encoded = encodeScheduleView(selection, orders);
    const parsed = parseScheduleView(encoded);
    if (!parsed.bytes) return null;
    return unpackSections(parsed.bytes, [
      { ref: orders.ucOrder },
      { ref: orders.turmaOrder },
      { ref: [...SCHEDULE_VIEW_DAYS] },
      { ref: orders.weekOrder },
    ]);
  }

  it("preserves a partial UC selection", () => {
    const sections = roundTrip({
      degreeId: "deg-aaaa",
      ano: "1",
      ucs: ["UC2", "UC4"],
      turmas: [],
      dias: [],
      semanas: [],
    });
    expect(sections?.[0]).toEqual({ values: ["UC2", "UC4"], isAll: false });
  });

  it("preserves a partial turma selection", () => {
    const sections = roundTrip({
      degreeId: "deg-aaaa",
      ano: "1",
      ucs: [],
      turmas: ["1A", "2B"],
      dias: [],
      semanas: [],
    });
    expect(sections?.[1]).toEqual({ values: ["1A", "2B"], isAll: false });
  });

  it("preserves a partial day selection", () => {
    const sections = roundTrip({
      degreeId: "deg-aaaa",
      ano: "1",
      ucs: [],
      turmas: [],
      dias: ["monday", "wednesday"],
      semanas: [],
    });
    expect(sections?.[2]).toEqual({ values: ["monday", "wednesday"], isAll: false });
  });

  it("preserves a partial weeks selection", () => {
    const sections = roundTrip({
      degreeId: "deg-aaaa",
      ano: "1",
      ucs: [],
      turmas: [],
      dias: [],
      semanas: ["w1", "w3"],
    });
    expect(sections?.[3]).toEqual({ values: ["w1", "w3"], isAll: false });
  });

  it("decodes unfiltered sections as empty with isAll=false", () => {
    // Encode a UC filter so bytes are emitted; the other sections are at
    // their defaults and should come back as `{ values: [], isAll: false }`
    // rather than the old "all-bits-set, isAll: true" collapse, so the
    // consumer can tell "no filter active" apart from "explicit pick of
    // every reference value".
    const sections = roundTrip({
      degreeId: "deg-aaaa",
      ano: "1",
      ucs: ["UC1"],
      turmas: [],
      dias: [],
      semanas: [],
    });
    expect(sections?.[1]).toEqual({ values: [], isAll: false });
    expect(sections?.[2]).toEqual({ values: [], isAll: false });
    expect(sections?.[3]).toEqual({ values: [], isAll: false });
  });

  it("preserves an explicit pick of every reference value as isAll", () => {
    const sections = roundTrip({
      degreeId: "deg-aaaa",
      ano: "1",
      ucs: ["UC1", "UC2", "UC3", "UC4", "UC5"],
      turmas: [],
      dias: [],
      semanas: [],
    });
    expect(sections?.[0]).toEqual({
      values: ["UC1", "UC2", "UC3", "UC4", "UC5"],
      isAll: true,
    });
  });

  it("collapses the all-weekdays dias state to 'no filter' in the URL", () => {
    const encoded = encodeScheduleView(
      {
        degreeId: "deg-aaaa",
        ano: "1",
        ucs: [],
        turmas: [],
        dias: [...SCHEDULE_VIEW_DAYS],
        semanas: [],
      },
      orders,
    );
    expect(encoded.split(":").length).toBe(2);
  });
});
