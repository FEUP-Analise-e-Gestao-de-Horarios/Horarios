import { describe, expect, it } from "vitest";
import { compareTurmas, compareTurnos } from "./useScheduleFilters";

describe("compareTurnos", () => {
  it("orders regular turnos numerically", () => {
    expect(["2", "10", "1"].sort(compareTurnos)).toEqual(["1", "2", "10"]);
  });

  it("sorts turno 0 last", () => {
    expect(["0", "2", "1"].sort(compareTurnos)).toEqual(["1", "2", "0"]);
  });

  it("keeps turno 0 last even against double-digit turnos", () => {
    expect(["10", "0", "3"].sort(compareTurnos)).toEqual(["3", "10", "0"]);
  });
});

describe("compareTurmas", () => {
  it("orders turma codes by numeric suffix, not lexically", () => {
    expect(["1LEIC10", "1LEIC8", "1LEIC9"].sort(compareTurmas)).toEqual([
      "1LEIC8",
      "1LEIC9",
      "1LEIC10",
    ]);
  });

  it("handles zero-padded codes", () => {
    expect(["1LEIC08", "1LEIC10", "1LEIC09"].sort(compareTurmas)).toEqual([
      "1LEIC08",
      "1LEIC09",
      "1LEIC10",
    ]);
  });
});
