import { describe, expect, it } from "vitest";
import { hhmmToMinutes, minutesToTime } from "./time";

describe("hhmmToMinutes", () => {
  it("converts midnight", () => {
    expect(hhmmToMinutes(0)).toBe(0);
  });

  it("handles on-the-hour times", () => {
    expect(hhmmToMinutes(800)).toBe(8 * 60);
    expect(hhmmToMinutes(1900)).toBe(19 * 60);
  });

  it("handles half-hour times", () => {
    expect(hhmmToMinutes(1430)).toBe(14 * 60 + 30);
    expect(hhmmToMinutes(800 + 45)).toBe(8 * 60 + 45);
  });

  it("handles end-of-day", () => {
    expect(hhmmToMinutes(2359)).toBe(23 * 60 + 59);
  });
});

describe("minutesToTime", () => {
  it("zero-pads hours and minutes", () => {
    expect(minutesToTime(0)).toBe("00:00");
    expect(minutesToTime(9 * 60 + 5)).toBe("09:05");
  });

  it("formats common schedule times", () => {
    expect(minutesToTime(8 * 60)).toBe("08:00");
    expect(minutesToTime(14 * 60 + 30)).toBe("14:30");
    expect(minutesToTime(19 * 60 + 30)).toBe("19:30");
  });

  it("formats end-of-day", () => {
    expect(minutesToTime(23 * 60 + 59)).toBe("23:59");
  });

  it("round-trips with hhmmToMinutes for typical schedule times", () => {
    for (const hhmm of [800, 830, 1200, 1230, 1900, 1930]) {
      const minutes = hhmmToMinutes(hhmm);
      const formatted = minutesToTime(minutes);
      const [hours, mins] = formatted.split(":").map(Number);
      expect(hours! * 100 + mins!).toBe(hhmm);
    }
  });
});
