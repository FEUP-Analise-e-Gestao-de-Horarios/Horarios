import { describe, expect, it } from "vitest";
import {
  createSubjectPalette,
  DEFAULT_SUBJECT_STYLE,
  PALETTE_SIZE,
  styleForSubject,
  type SubjectPalette,
} from "./subjectColors";

const HEX = /^#[0-9a-f]{6}$/;

// One distinct UC name per palette slot.
const FULL = Array.from({ length: PALETTE_SIZE }, (_, i) => `UC${i}`);

describe("createSubjectPalette", () => {
  it("provides at least 30 distinct hues", () => {
    expect(PALETTE_SIZE).toBeGreaterThanOrEqual(30);
    const palette = createSubjectPalette(FULL);
    // Compare on the chip tone (one tone per hue) → all backgrounds distinct.
    const backgrounds = FULL.map((uc) => styleForSubject(palette, uc).background);
    expect(new Set(backgrounds).size).toBe(PALETTE_SIZE);
  });

  it("assigns colours deterministically by name", () => {
    const a = createSubjectPalette(["Algoritmos", "Bases de Dados"]);
    const b = createSubjectPalette(["Algoritmos", "Bases de Dados"]);
    expect(styleForSubject(a, "Algoritmos", "TP")).toEqual(styleForSubject(b, "Algoritmos", "TP"));
  });

  it("cycles back to the first hue once UCs exceed the palette size", () => {
    const palette = createSubjectPalette([...FULL, "WRAP"]);
    expect(styleForSubject(palette, "WRAP", "TP")).toEqual(styleForSubject(palette, FULL[0], "TP"));
  });

  it("ignores duplicate names, keeping the first assignment", () => {
    const palette = createSubjectPalette(["X", "Y", "X"]);
    expect(styleForSubject(palette, "X", "TP")).not.toBe(DEFAULT_SUBJECT_STYLE);
    expect(styleForSubject(palette, "Y", "TP")).not.toBe(DEFAULT_SUBJECT_STYLE);
  });
});

describe("styleForSubject", () => {
  const palette: SubjectPalette = createSubjectPalette(["Algoritmos"]);

  it("returns the default style when the palette or UC is missing", () => {
    expect(styleForSubject(undefined, "Algoritmos", "TP")).toBe(DEFAULT_SUBJECT_STYLE);
    expect(styleForSubject(palette, "Desconhecida", "TP")).toBe(DEFAULT_SUBJECT_STYLE);
    expect(styleForSubject(palette, undefined, "TP")).toBe(DEFAULT_SUBJECT_STYLE);
    expect(styleForSubject(palette, "", "TP")).toBe(DEFAULT_SUBJECT_STYLE);
  });

  it("returns CSS hex colours, not Tailwind classes", () => {
    const style = styleForSubject(palette, "Algoritmos", "TP");
    expect(style.background).toMatch(HEX);
    expect(style.border).toMatch(HEX);
    expect(style.text).toMatch(HEX);
  });

  it("gives T, TP, P and PL distinct shades of the same hue", () => {
    const t = styleForSubject(palette, "Algoritmos", "T");
    const tp = styleForSubject(palette, "Algoritmos", "TP");
    const p = styleForSubject(palette, "Algoritmos", "P");
    const pl = styleForSubject(palette, "Algoritmos", "PL");
    const backgrounds = [t, tp, p, pl].map((s) => s.background);
    // All four tones are visually distinct…
    expect(new Set(backgrounds).size).toBe(4);
    // …and ordered lightest (T) to strongest (PL).
    expect(t.background > tp.background).toBe(true); // lighter hex → larger string
    // …but share one hue, proved by the common text colour.
    expect(new Set([t, tp, p, pl].map((s) => s.text)).size).toBe(1);
  });

  it("uses the middle tone for unknown types", () => {
    const unknown = styleForSubject(palette, "Algoritmos", "ZZ");
    const tp = styleForSubject(palette, "Algoritmos", "TP");
    expect(unknown.background).toBe(tp.background);
  });

  it("returns the chip tone when no type is given (navbar dropdown)", () => {
    expect(styleForSubject(palette, "Algoritmos").background).toMatch(HEX);
  });
});
