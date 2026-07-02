import { useMemo } from "react";
import { hhmmToMinutes } from "@/utils/time";
import type { WeekGridEvent, WeekGridMark } from "./WeekGrid";

const SLOT_MINUTES = 30;
const DEFAULT_START_HHMM = 800;
const DEFAULT_END_HHMM = 2000;

interface UseGridTimeRangeParams {
  events: WeekGridEvent[];
  marks: WeekGridMark[];
  /** Inclusive hard lower bound (HHMM). When omitted, grows to fit events/marks. */
  startTime: number | undefined;
  /** Exclusive hard upper bound (HHMM). When omitted, grows to fit events/marks. */
  endTime: number | undefined;
  /** Whether to render an extra empty slot row past `endTime`. */
  includeEndSlot: boolean;
}

/**
 * Resolves the time range the week grid should render: a start in minutes
 * since midnight (`gridStartMinutes`) and the number of half-hour slots
 * (`slotCount`). Both `startTime` and `endTime` can be `undefined` to let the
 * range auto-fit around the events and marks; if either is set, that bound is
 * fixed.
 */
export function useGridTimeRange({
  events,
  marks,
  startTime,
  endTime,
  includeEndSlot,
}: UseGridTimeRangeParams): { gridStartMinutes: number; slotCount: number } {
  return useMemo(() => {
    let min = hhmmToMinutes(startTime ?? DEFAULT_START_HHMM);
    let max = hhmmToMinutes(endTime ?? DEFAULT_END_HHMM);

    if (startTime === undefined || endTime === undefined) {
      for (const ev of events) {
        const start = hhmmToMinutes(ev.startTime);
        const end = start + ev.duration * SLOT_MINUTES;
        if (startTime === undefined && start < min) min = Math.floor(start / 60) * 60;
        if (endTime === undefined && end > max) max = Math.ceil(end / 60) * 60;
      }
      for (const m of marks) {
        const t = hhmmToMinutes(m.time);
        if (startTime === undefined && t < min) min = Math.floor(t / 60) * 60;
        if (endTime === undefined && t + SLOT_MINUTES > max) {
          max = Math.ceil((t + SLOT_MINUTES) / 60) * 60;
        }
      }
    }

    const count = (max - min) / SLOT_MINUTES + (includeEndSlot ? 1 : 0);
    return { gridStartMinutes: min, slotCount: Math.max(count, 1) };
  }, [events, marks, startTime, endTime, includeEndSlot]);
}
