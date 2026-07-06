import { Fragment } from "react";
import type { RedBlockBase } from "@/types/project/red_block";
import { WEEKDAYS, WEEKDAY_LABELS_SHORT } from "@/utils/weekdays";

const START_MINUTES = 8 * 60;
const END_MINUTES = 20 * 60;
const SLOT_MINUTES = 30;

/** 30-min slot starts as HHMM ints (800, 830, …) across the schedule window. */
function slotHhmms(): number[] {
  const slots: number[] = [];
  for (let m = START_MINUTES; m < END_MINUTES; m += SLOT_MINUTES) {
    slots.push(Math.floor(m / 60) * 100 + (m % 60));
  }
  return slots;
}

/**
 * Compact weekday × time grid marking a teacher's/room's unavailable slots
 * (`red_blocks`) in red — the hover-tooltip body for PI ToDo #4.
 */
export default function MiniAvailabilityGrid({
  redBlocks,
  fill = false,
}: {
  redBlocks: RedBlockBase[];
  /** Stretch the day columns to fill the tooltip width instead of fixed 12px. */
  fill?: boolean;
}) {
  const blocked = new Set(redBlocks.map((block) => `${block.weekday}-${block.hour}`));
  const slots = slotHhmms();
  const dayColumn = fill ? "minmax(12px, 1fr)" : "12px";

  return (
    <div
      className={`gap-px ${fill ? "grid w-full" : "inline-grid"}`}
      style={{ gridTemplateColumns: `auto repeat(${WEEKDAYS.length}, ${dayColumn})` }}
    >
      <div />
      {WEEKDAYS.map((weekday) => (
        <div key={weekday} className="text-center text-[8px] leading-none text-[#6b6375]">
          {WEEKDAY_LABELS_SHORT[weekday][0]}
        </div>
      ))}
      {slots.map((hhmm) => (
        <Fragment key={hhmm}>
          <div className="pr-1 text-right text-[8px] leading-[8px] text-[#6b6375] tabular-nums">
            {hhmm % 100 === 0 ? `${hhmm / 100}h` : ""}
          </div>
          {WEEKDAYS.map((weekday) => (
            <div
              key={weekday}
              className={`h-2 rounded-[1px] ${
                blocked.has(`${weekday}-${hhmm}`) ? "bg-[#e5484d]" : "bg-[#eceaf0]"
              }`}
            />
          ))}
        </Fragment>
      ))}
    </div>
  );
}
