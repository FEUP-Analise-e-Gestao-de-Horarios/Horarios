import { describe, expect, it } from "vitest";
import {
  turnosFromTurmas,
  turnoTurmaUpdateForTurmaChange,
  turnoTurmaUpdateForTurnoChange,
} from "./useTurnoTurmaSync";

const CLASSES = [
  { code: "1A", shift: 1 },
  { code: "1B", shift: 1 },
  { code: "2A", shift: 2 },
  { code: "2B", shift: 2 },
  { code: "3A", shift: 3 },
];
const TURMA_ORDER = ["1A", "1B", "2A", "2B", "3A"];
const TURNO_ORDER = ["1", "2", "3"];

describe("turnosFromTurmas", () => {
  it("returns the unique, ascending shifts the turmas belong to", () => {
    expect(turnosFromTurmas(CLASSES, ["2A", "1B", "3A"])).toEqual(["1", "2", "3"]);
  });

  it("returns [] when no turmas are selected", () => {
    expect(turnosFromTurmas(CLASSES, [])).toEqual([]);
  });

  it("ignores turmas the class list doesn't know about", () => {
    expect(turnosFromTurmas(CLASSES, ["1A", "9Z"])).toEqual(["1"]);
  });
});

describe("turnoTurmaUpdateForTurnoChange", () => {
  it("adds every turma in a newly-selected turno", () => {
    expect(
      turnoTurmaUpdateForTurnoChange({
        prevTurnos: ["1"],
        nextTurnos: ["1", "2"],
        prevTurmas: ["1A", "1B"],
        classes: CLASSES,
        turnoOrder: TURNO_ORDER,
        turmaOrder: TURMA_ORDER,
      }),
    ).toEqual({ turmas: ["1A", "1B", "2A", "2B"], turnos: ["1", "2"] });
  });

  it("drops every turma in a newly-deselected turno", () => {
    expect(
      turnoTurmaUpdateForTurnoChange({
        prevTurnos: ["1", "2"],
        nextTurnos: ["2"],
        prevTurmas: ["1A", "1B", "2A"],
        classes: CLASSES,
        turnoOrder: TURNO_ORDER,
        turmaOrder: TURMA_ORDER,
      }),
    ).toEqual({ turmas: ["2A"], turnos: ["2"] });
  });

  it("returns empty when all turnos are cleared", () => {
    expect(
      turnoTurmaUpdateForTurnoChange({
        prevTurnos: ["1", "2"],
        nextTurnos: [],
        prevTurmas: ["1A", "2A"],
        classes: CLASSES,
        turnoOrder: TURNO_ORDER,
        turmaOrder: TURMA_ORDER,
      }),
    ).toEqual({ turmas: [], turnos: [] });
  });

  it("sorts turmas by turmaOrder regardless of insertion order", () => {
    expect(
      turnoTurmaUpdateForTurnoChange({
        prevTurnos: ["3"],
        nextTurnos: ["3", "1"],
        prevTurmas: ["3A"],
        classes: CLASSES,
        turnoOrder: TURNO_ORDER,
        turmaOrder: TURMA_ORDER,
      }).turmas,
    ).toEqual(["1A", "1B", "3A"]);
  });
});

describe("turnoTurmaUpdateForTurmaChange", () => {
  it("derives turnos from the surviving turmas", () => {
    expect(
      turnoTurmaUpdateForTurmaChange({
        nextTurmas: ["1A", "2B"],
        classes: CLASSES,
        turnoOrder: TURNO_ORDER,
        turmaOrder: TURMA_ORDER,
      }),
    ).toEqual({ turmas: ["1A", "2B"], turnos: ["1", "2"] });
  });

  it("drops turmas the class list doesn't have", () => {
    expect(
      turnoTurmaUpdateForTurmaChange({
        nextTurmas: ["1A", "9Z"],
        classes: CLASSES,
        turnoOrder: TURNO_ORDER,
        turmaOrder: TURMA_ORDER,
      }),
    ).toEqual({ turmas: ["1A"], turnos: ["1"] });
  });

  it("returns empty when no turmas remain", () => {
    expect(
      turnoTurmaUpdateForTurmaChange({
        nextTurmas: [],
        classes: CLASSES,
        turnoOrder: TURNO_ORDER,
        turmaOrder: TURMA_ORDER,
      }),
    ).toEqual({ turmas: [], turnos: [] });
  });

  it("sorts the output by turma and turno order", () => {
    const { turmas, turnos } = turnoTurmaUpdateForTurmaChange({
      nextTurmas: ["3A", "1A", "2A"],
      classes: CLASSES,
      turnoOrder: TURNO_ORDER,
      turmaOrder: TURMA_ORDER,
    });
    expect(turmas).toEqual(["1A", "2A", "3A"]);
    expect(turnos).toEqual(["1", "2", "3"]);
  });
});
