import { describe, expect, it } from "vitest";
import { compareTurnos } from "./useScheduleFilters";

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
