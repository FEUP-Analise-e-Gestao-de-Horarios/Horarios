import { useReducer } from "react";
import type { Weekday } from "@/types/project/weekday";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import type { WeekGridEvent } from "./WeekGrid";

const MIN_TIME_MINUTES = 8 * 60;
const MAX_TIME_MINUTES = 19 * 60 + 30;
const MIN_DURATION_MINUTES = 30;

function clampTimeMinutes(totalMinutes: number): number {
  return Math.max(MIN_TIME_MINUTES, Math.min(MAX_TIME_MINUTES, totalMinutes));
}

function timeToMinutes(time: string): number | null {
  const [hours, minutes] = time.split(":").map(Number);
  if (hours === undefined || minutes === undefined || Number.isNaN(hours) || Number.isNaN(minutes))
    return null;
  return hours * 60 + minutes;
}

function shiftTimeByMinutes(time: string, deltaMinutes: number): string {
  const totalMinutes = timeToMinutes(time);
  if (totalMinutes === null) return time;
  return minutesToTime(clampTimeMinutes(totalMinutes + deltaMinutes));
}

function normalizeTimeValue(value: string, fallback: string): string {
  const cleaned = value.trim();
  const match = cleaned.match(/^(\d{1,2}):?(\d{2})$/);
  if (!match) return fallback;

  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (Number.isNaN(hours) || Number.isNaN(minutes)) return fallback;
  if (minutes < 0 || minutes > 59) return fallback;

  const totalMinutes = clampTimeMinutes(hours * 60 + minutes);
  return minutesToTime(totalMinutes);
}

/**
 * Adjusts `state` so `endTime` is at least one slot after `startTime`. The
 * pinned field stays put; the other is nudged into range.
 */
function enforceTimeOrdering(state: EventDrawerFormState, pinned: TimeField): EventDrawerFormState {
  const startMin = timeToMinutes(state.startTime);
  const endMin = timeToMinutes(state.endTime);
  if (startMin === null || endMin === null) return state;
  if (endMin - startMin >= MIN_DURATION_MINUTES) return state;

  if (pinned === "startTime") {
    const nextEnd = clampTimeMinutes(startMin + MIN_DURATION_MINUTES);
    return { ...state, endTime: minutesToTime(nextEnd) };
  }
  const nextStart = clampTimeMinutes(endMin - MIN_DURATION_MINUTES);
  return { ...state, startTime: minutesToTime(nextStart) };
}

function toggleSelection(current: string[], itemId: string): string[] {
  return current.includes(itemId)
    ? current.filter((selectedId) => selectedId !== itemId)
    : [...current, itemId];
}

export type EventDrawerFormState = {
  selectedUcOverride: string;
  selectedDocenteOverride: string[];
  selectedSalaOverride: string[];
  selectedTurmasOverride: string[];
  selectedWeekday: Weekday;
  startTime: string;
  endTime: string;
};

type TimeField = "startTime" | "endTime";

export type EventDrawerFormAction =
  | { type: "reset"; event: WeekGridEvent | null | undefined }
  | { type: "setUc"; value: string }
  | { type: "setWeekday"; value: Weekday }
  | { type: "setTime"; field: TimeField; value: string }
  | { type: "shiftTime"; field: TimeField; delta: number }
  | { type: "normalizeTime"; field: TimeField; raw: string }
  | { type: "toggleDocente"; id: string }
  | { type: "toggleSala"; id: string }
  | { type: "setTurmas"; value: string[] };

export function getInitialEventDrawerFormState(event?: WeekGridEvent | null): EventDrawerFormState {
  if (event) {
    return {
      selectedUcOverride: event.uc ?? "",
      selectedDocenteOverride: event.teacherIds ?? [],
      selectedSalaOverride: event.roomIds ?? [],
      selectedTurmasOverride: event.classCodes ?? (event.turma ? [event.turma] : []),
      selectedWeekday: event.weekday,
      startTime: minutesToTime(hhmmToMinutes(event.startTime)),
      endTime: minutesToTime(hhmmToMinutes(event.startTime) + event.duration * 30),
    };
  }
  return {
    selectedUcOverride: "",
    selectedDocenteOverride: [],
    selectedSalaOverride: [],
    selectedTurmasOverride: [],
    selectedWeekday: "monday",
    startTime: "10:30",
    endTime: "12:30",
  };
}

export function eventDrawerFormReducer(
  state: EventDrawerFormState,
  action: EventDrawerFormAction,
): EventDrawerFormState {
  switch (action.type) {
    case "reset":
      return getInitialEventDrawerFormState(action.event);
    case "setUc":
      return { ...state, selectedUcOverride: action.value };
    case "setWeekday":
      return { ...state, selectedWeekday: action.value };
    case "setTime":
      // Free-text edits skip the ordering invariant — the user is mid-type;
      // ordering is enforced on blur via `normalizeTime`.
      return { ...state, [action.field]: action.value };
    case "shiftTime":
      return enforceTimeOrdering(
        { ...state, [action.field]: shiftTimeByMinutes(state[action.field], action.delta) },
        action.field,
      );
    case "normalizeTime":
      return enforceTimeOrdering(
        { ...state, [action.field]: normalizeTimeValue(action.raw, state[action.field]) },
        action.field,
      );
    case "toggleDocente":
      return {
        ...state,
        selectedDocenteOverride: toggleSelection(state.selectedDocenteOverride, action.id),
      };
    case "toggleSala":
      return {
        ...state,
        selectedSalaOverride: toggleSelection(state.selectedSalaOverride, action.id),
      };
    case "setTurmas":
      return { ...state, selectedTurmasOverride: action.value };
  }
}

/**
 * Owns the edit-drawer form state for an event being edited.
 *
 * The parent (`SchedulePage`) remounts this hook with `key={event.id}` per
 * event, so the initial state is derived once from `event` and subsequent
 * field edits live entirely inside the reducer.
 */
export function useEventDrawerForm(event?: WeekGridEvent | null) {
  return useReducer(eventDrawerFormReducer, event, getInitialEventDrawerFormState);
}

/** Re-exported helper for callers that need the same toggle semantics. */
export { toggleSelection };
