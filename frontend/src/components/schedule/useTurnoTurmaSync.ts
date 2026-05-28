import { useCallback } from "react";
import { sortValuesByReference } from "@/utils/scheduleEvents";

type TurnoTurmaClass = { code: string; shift: number };

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
  const turnosFromTurmas = useCallback(
    (turmaCodes: string[]) => {
      const selectedShifts = new Set<string>();
      for (const classItem of classes) {
        if (turmaCodes.includes(classItem.code)) {
          selectedShifts.add(String(classItem.shift));
        }
      }
      return [...selectedShifts].sort((a, b) => Number(a) - Number(b));
    },
    [classes],
  );

  const handleSelectTurnos = useCallback(
    (nextTurnos: string[]) => {
      const addedTurnos = nextTurnos.filter((turno) => !effectiveTurnos.includes(turno));
      const removedTurnos = effectiveTurnos.filter((turno) => !nextTurnos.includes(turno));

      const turmasToAdd = classes
        .filter((classItem) => addedTurnos.includes(String(classItem.shift)))
        .map((classItem) => classItem.code);
      const turmasToRemove = classes
        .filter((classItem) => removedTurnos.includes(String(classItem.shift)))
        .map((classItem) => classItem.code);

      const nextTurmas = new Set(effectiveTurmas);
      turmasToAdd.forEach((turma) => nextTurmas.add(turma));
      turmasToRemove.forEach((turma) => nextTurmas.delete(turma));

      const nextTurmasArray = [...nextTurmas].filter((turma) =>
        classes.some((classItem) => classItem.code === turma),
      );

      const orderedTurmas = sortValuesByReference(nextTurmasArray, turmaOrder);
      const orderedTurnos = sortValuesByReference(turnosFromTurmas(orderedTurmas), turnoOrder);

      setTurmas(orderedTurmas);
      setTurnos(orderedTurnos);
    },
    [
      classes,
      effectiveTurmas,
      effectiveTurnos,
      setTurmas,
      setTurnos,
      turmaOrder,
      turnoOrder,
      turnosFromTurmas,
    ],
  );

  const handleSelectTurmas = useCallback(
    (nextTurmas: string[]) => {
      const validTurmas = nextTurmas.filter((turma) =>
        classes.some((classItem) => classItem.code === turma),
      );
      const orderedTurmas = sortValuesByReference(validTurmas, turmaOrder);
      setTurmas(orderedTurmas);
      setTurnos(sortValuesByReference(turnosFromTurmas(orderedTurmas), turnoOrder));
    },
    [classes, setTurmas, setTurnos, turmaOrder, turnoOrder, turnosFromTurmas],
  );

  return { handleSelectTurnos, handleSelectTurmas };
}
