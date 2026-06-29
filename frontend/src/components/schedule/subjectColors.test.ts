import { describe, expect, it } from "vitest";
import {
  DEFAULT_SUBJECT_STYLE,
  DEFAULT_SUBJECT_STYLE_DARK,
  styleForSubject,
  styleForSubjectDark,
} from "./subjectColors";

describe("styleForSubject", () => {
  it("returns the default style for undefined", () => {
    expect(styleForSubject(undefined)).toBe(DEFAULT_SUBJECT_STYLE);
  });

  it("returns the default style for the empty string", () => {
    expect(styleForSubject("")).toBe(DEFAULT_SUBJECT_STYLE);
  });

  it("returns the same style for the same subject (stability)", () => {
    expect(styleForSubject("Algoritmos")).toBe(styleForSubject("Algoritmos"));
  });

  it("returns a SubjectStyle with the bg/border/text triplet", () => {
    const style = styleForSubject("Algoritmos");
    expect(style).toHaveProperty("bg");
    expect(style).toHaveProperty("border");
    expect(style).toHaveProperty("text");
  });

  it("never returns the default style for a real subject name", () => {
    // The hash should land in [0, palette.length); only undefined / empty
    // string short-circuit to the default.
    for (const name of ["A", "AA", "Algorítmos", "Lógica", "X".repeat(100)]) {
      expect(styleForSubject(name)).not.toBe(DEFAULT_SUBJECT_STYLE);
    }
  });

  it("normalises hashes that would otherwise be negative to a positive palette index", () => {
    // Long inputs let the int32 hash wrap negative; the bug-fix referenced in
    // subjectColors guards against `(-x % n)` returning negative.
    const longName = "z".repeat(200);
    const style = styleForSubject(longName);
    expect(style).toHaveProperty("bg");
    expect(style.bg).toMatch(/^bg-/);
  });
});

describe("styleForSubjectDark", () => {
  it("returns the dark default for undefined", () => {
    expect(styleForSubjectDark(undefined)).toBe(DEFAULT_SUBJECT_STYLE_DARK);
  });

  it("returns the dark default for the empty string", () => {
    expect(styleForSubjectDark("")).toBe(DEFAULT_SUBJECT_STYLE_DARK);
  });

  it("returns the same dark style for the same subject (stability)", () => {
    expect(styleForSubjectDark("Algoritmos")).toBe(styleForSubjectDark("Algoritmos"));
  });

  it("returns a dark variant (using /15 alpha bg) for a real subject name", () => {
    const style = styleForSubjectDark("Algoritmos");
    expect(style.bg).toMatch(/\/15$/);
  });

  it("pairs light and dark variants from the same palette index for the same subject", () => {
    // Both lookups use the same hash; they should pick the same palette entry,
    // i.e. the colour family agrees (e.g. both blue).
    const subject = "Programação";
    const light = styleForSubject(subject);
    const dark = styleForSubjectDark(subject);
    const lightColor = light.bg.replace(/^bg-/, "").split("-")[0];
    const darkColor = dark.bg.replace(/^bg-/, "").split("-")[0];
    expect(lightColor).toBe(darkColor);
  });
});
