import { describe, expect, it } from "vitest";
import { formatDurationSlots } from "@/utils/time";
import type { WeekGridEvent } from "./WeekGrid";
import {
  eventDrawerFormReducer,
  getInitialEventDrawerFormState,
  type EventDrawerFormState,
} from "./useEventDrawerForm";

function baseState(overrides: Partial<EventDrawerFormState> = {}): EventDrawerFormState {
  return { ...getInitialEventDrawerFormState(null), ...overrides };
}

describe("getInitialEventDrawerFormState", () => {
  it("seeds duration from the event's slot count", () => {
    const event = { startTime: 1030, duration: 4, weekday: "monday" } as WeekGridEvent;
    const state = getInitialEventDrawerFormState(event);
    expect(state.startTime).toBe("10:30");
    expect(state.durationSlots).toBe(4);
  });

  it("clamps a duration that would overrun the grid end", () => {
    const event = { startTime: 1830, duration: 8, weekday: "monday" } as WeekGridEvent;
    // 18:30 leaves only three 30-min slots before the 20:00 grid end.
    expect(getInitialEventDrawerFormState(event).durationSlots).toBe(3);
  });

  it("clamps a seeded start past the latest allowed slot", () => {
    const event = { startTime: 2000, duration: 2, weekday: "monday" } as WeekGridEvent;
    // 20:00 is past the 19:30 latest start; pull it back to the last valid slot.
    const state = getInitialEventDrawerFormState(event);
    expect(state.startTime).toBe("19:30");
    expect(state.durationSlots).toBe(1);
  });
});

describe("eventDrawerFormReducer — duration", () => {
  it("never drops below one slot", () => {
    const next = eventDrawerFormReducer(baseState({ durationSlots: 1 }), {
      type: "shiftDuration",
      delta: -1,
    });
    expect(next.durationSlots).toBe(1);
  });

  it("caps the duration at what fits after the start time", () => {
    const next = eventDrawerFormReducer(baseState({ startTime: "18:00", durationSlots: 2 }), {
      type: "setDuration",
      slots: 10,
    });
    // 18:00 -> 20:00 is four slots.
    expect(next.durationSlots).toBe(4);
  });

  it("re-clamps the duration when the start time moves later", () => {
    const next = eventDrawerFormReducer(baseState({ startTime: "08:00", durationSlots: 20 }), {
      type: "shiftStartTime",
      delta: 600,
    });
    expect(next.startTime).toBe("18:00");
    expect(next.durationSlots).toBe(4);
  });
});

describe("formatDurationSlots", () => {
  it("formats slot counts as duration labels", () => {
    expect(formatDurationSlots(1)).toBe("30min");
    expect(formatDurationSlots(2)).toBe("1h");
    expect(formatDurationSlots(3)).toBe("1h30");
  });
});
