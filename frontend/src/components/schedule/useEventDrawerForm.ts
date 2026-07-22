import { useReducer } from "react";
import type { Weekday } from "@/types/project/weekday";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import type { WeekGridEvent } from "./WeekGrid";

const SLOT_MINUTES = 30;
const MIN_TIME_MINUTES = 7 * 60;
const MAX_END_MINUTES = 20 * 60;
// A class needs at least one slot before the grid ends, so it can't start later
// than 19:30.
const MAX_START_MINUTES = MAX_END_MINUTES - SLOT_MINUTES;
const MIN_DURATION_SLOTS = 1;

function clampTimeMinutes(totalMinutes: number): number {
  return Math.max(MIN_TIME_MINUTES, Math.min(MAX_START_MINUTES, totalMinutes));
}

/** Largest duration (in slots) that keeps `startTime` + duration within the grid. */
function maxDurationSlots(startTime: string): number {
  const startMin = timeToMinutes(startTime) ?? MIN_TIME_MINUTES;
  return Math.max(MIN_DURATION_SLOTS, Math.floor((MAX_END_MINUTES - startMin) / SLOT_MINUTES));
}

function clampDuration(slots: number, startTime: string): number {
  return Math.max(MIN_DURATION_SLOTS, Math.min(maxDurationSlots(startTime), slots));
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
  /** Class length in 30-min slots (PI ToDo #19 — replaces an explicit end time). */
  durationSlots: number;
};

export type EventDrawerFormAction =
  | { type: "reset"; event: WeekGridEvent | null | undefined }
  | { type: "setUc"; value: string }
  | { type: "setWeekday"; value: Weekday }
  | { type: "setStartTime"; value: string }
  | { type: "shiftStartTime"; delta: number }
  | { type: "normalizeStartTime"; raw: string }
  | { type: "setDuration"; slots: number }
  | { type: "shiftDuration"; delta: number }
  | { type: "toggleDocente"; id: string }
  | { type: "toggleSala"; id: string }
  | { type: "setTurmas"; value: string[] }
  | { type: "placeAt"; weekday: Weekday; minutes: number; turma?: string };

export function getInitialEventDrawerFormState(event?: WeekGridEvent | null): EventDrawerFormState {
  if (event) {
    // Clamp the seeded start the same way shifts/normalization do, so an event
    // starting past the latest allowed slot doesn't open the drawer out of range.
    const startTime = minutesToTime(clampTimeMinutes(hhmmToMinutes(event.startTime)));
    return {
      selectedUcOverride: event.uc ?? "",
      selectedDocenteOverride: (event.teachers ?? []).map((teacher) => teacher.id),
      selectedSalaOverride: (event.rooms ?? []).map((room) => room.id),
      selectedTurmasOverride: event.classCodes ?? (event.turma ? [event.turma] : []),
      selectedWeekday: event.weekday,
      startTime,
      durationSlots: clampDuration(event.duration, startTime),
    };
  }
  return {
    selectedUcOverride: "",
    selectedDocenteOverride: [],
    selectedSalaOverride: [],
    selectedTurmasOverride: [],
    selectedWeekday: "monday",
    startTime: "10:30",
    durationSlots: 4,
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
    case "setStartTime":
      // Free-text edits stay raw — the user is mid-type; the value is parsed and
      // clamped on blur via `normalizeStartTime`.
      return { ...state, startTime: action.value };
    case "shiftStartTime": {
      const startTime = shiftTimeByMinutes(state.startTime, action.delta);
      // A later start can shrink the room left in the grid, so re-clamp duration.
      return { ...state, startTime, durationSlots: clampDuration(state.durationSlots, startTime) };
    }
    case "normalizeStartTime": {
      const startTime = normalizeTimeValue(action.raw, state.startTime);
      return { ...state, startTime, durationSlots: clampDuration(state.durationSlots, startTime) };
    }
    case "setDuration":
      return { ...state, durationSlots: clampDuration(action.slots, state.startTime) };
    case "shiftDuration":
      return {
        ...state,
        durationSlots: clampDuration(state.durationSlots + action.delta, state.startTime),
      };
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
    case "placeAt": {
      const startTime = minutesToTime(clampTimeMinutes(action.minutes));
      // Clicking inside a turma the event already spans just moves it in
      // time; clicking a turma it doesn't have reassigns it to that one
      // class alone — a deliberate move, not a multi-turma split.
      const selectedTurmasOverride =
        action.turma && !state.selectedTurmasOverride.includes(action.turma)
          ? [action.turma]
          : state.selectedTurmasOverride;
      return { ...state, selectedWeekday: action.weekday, startTime, selectedTurmasOverride };
    }
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
