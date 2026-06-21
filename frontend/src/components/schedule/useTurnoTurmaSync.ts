import { useCallback } from "react";
import { sortValuesByReference } from "@/utils/scheduleEvents";

type TurnoTurmaClass = { code: string; shift: number };

export function turnosFromTurmas(
  classes: readonly TurnoTurmaClass[],
  turmaCodes: readonly string[],
): string[] {
  const selectedShifts = new Set<string>();
  for (const classItem of classes) {
    if (turmaCodes.includes(classItem.code)) {
      selectedShifts.add(String(classItem.shift));
    }
  }
  return [...selectedShifts].sort((a, b) => Number(a) - Number(b));
}

/**
 * Returns the {turmas, turnos} pair that should replace the current selection
 * after the user changed the turno selection from `prevTurnos` to `nextTurnos`.
 * Adds every turma belonging to a newly-selected turno; drops every turma
 * belonging to a newly-deselected turno; preserves the rest. Both outputs are
 * sorted by the canonical reference order.
 */
export function turnoTurmaUpdateForTurnoChange(params: {
  prevTurnos: string[];
  nextTurnos: string[];
  prevTurmas: string[];
  classes: readonly TurnoTurmaClass[];
  turnoOrder: string[];
  turmaOrder: string[];
}): { turmas: string[]; turnos: string[] } {
  const { prevTurnos, nextTurnos, prevTurmas, classes, turnoOrder, turmaOrder } = params;
  const addedTurnos = nextTurnos.filter((turno) => !prevTurnos.includes(turno));
  const removedTurnos = prevTurnos.filter((turno) => !nextTurnos.includes(turno));

  const turmasToAdd = classes
    .filter((classItem) => addedTurnos.includes(String(classItem.shift)))
    .map((classItem) => classItem.code);
  const turmasToRemove = classes
    .filter((classItem) => removedTurnos.includes(String(classItem.shift)))
    .map((classItem) => classItem.code);

  const next = new Set(prevTurmas);
  turmasToAdd.forEach((turma) => next.add(turma));
  turmasToRemove.forEach((turma) => next.delete(turma));

  const validNext = [...next].filter((turma) =>
    classes.some((classItem) => classItem.code === turma),
  );
  const orderedTurmas = sortValuesByReference(validNext, turmaOrder);
  const orderedTurnos = sortValuesByReference(turnosFromTurmas(classes, orderedTurmas), turnoOrder);
  return { turmas: orderedTurmas, turnos: orderedTurnos };
}

/**
 * Returns the {turmas, turnos} pair that should replace the current selection
 * after the user changed the turma selection. Drops any turma the year doesn't
 * actually have (defensive) and derives the turnos from the remaining turmas.
 */
export function turnoTurmaUpdateForTurmaChange(params: {
  nextTurmas: string[];
  classes: readonly TurnoTurmaClass[];
  turnoOrder: string[];
  turmaOrder: string[];
}): { turmas: string[]; turnos: string[] } {
  const { nextTurmas, classes, turnoOrder, turmaOrder } = params;
  const validTurmas = nextTurmas.filter((turma) =>
    classes.some((classItem) => classItem.code === turma),
  );
  const orderedTurmas = sortValuesByReference(validTurmas, turmaOrder);
  const orderedTurnos = sortValuesByReference(turnosFromTurmas(classes, orderedTurmas), turnoOrder);
  return { turmas: orderedTurmas, turnos: orderedTurnos };
}

interface UseTurnoTurmaSyncParams {
  classes: TurnoTurmaClass[];
  turnoOrder: string[];
  turmaOrder: string[];
  effectiveTurnos: string[];
  effectiveTurmas: string[];
  setTurnos: (turnos: string[]) => void;
  setTurmas: (turmas: string[]) => void;
}

/**
 * Keeps the turno and turma selections in sync:
 *
 * - selecting/clearing a turno adds/removes every turma in that turno;
 * - changing the turma selection re-derives the turnos that still have at
 *   least one selected turma.
 *
 * Both handlers normalise their output to the canonical turno/turma order.
 */
export function useTurnoTurmaSync({
  classes,
  turnoOrder,
  turmaOrder,
  effectiveTurnos,
  effectiveTurmas,
  setTurnos,
  setTurmas,
}: UseTurnoTurmaSyncParams) {
  const handleSelectTurnos = useCallback(
    (nextTurnos: string[]) => {
      const { turmas, turnos } = turnoTurmaUpdateForTurnoChange({
        prevTurnos: effectiveTurnos,
        nextTurnos,
        prevTurmas: effectiveTurmas,
        classes,
        turnoOrder,
        turmaOrder,
      });
      setTurmas(turmas);
      setTurnos(turnos);
    },
    [classes, effectiveTurmas, effectiveTurnos, setTurmas, setTurnos, turmaOrder, turnoOrder],
  );

  const handleSelectTurmas = useCallback(
    (nextTurmas: string[]) => {
      const { turmas, turnos } = turnoTurmaUpdateForTurmaChange({
        nextTurmas,
        classes,
        turnoOrder,
        turmaOrder,
      });
      setTurmas(turmas);
      setTurnos(turnos);
    },
    [classes, setTurmas, setTurnos, turmaOrder, turnoOrder],
  );

  return { handleSelectTurnos, handleSelectTurmas };
}
