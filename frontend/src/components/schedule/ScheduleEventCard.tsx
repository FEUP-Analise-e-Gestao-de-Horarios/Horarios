import { type ReactNode } from "react";
import { hhmmToMinutes, minutesToTime } from "@/utils/time";
import { WEEKDAY_LABELS_LONG } from "@/utils/weekdays";
import type { WeekGridEvent } from "./WeekGrid";
import { RoomAvailability, TeacherHoverNames } from "./AvailabilityTooltipContent";
import { SCHEDULE_EVENT_DATA_ATTR } from "./dismissable";
import HoverTooltip from "./HoverTooltip";
import MarqueeText from "./MarqueeText";
import { SUBJECT_SELECTION_RING, type SubjectStyle } from "./subjectColors";

const SLOT_MINUTES = 30;

/** A card text element, optionally wrapped in a hover tooltip (PI ToDo #4). */
function Field({
  tip,
  className,
  children,
}: {
  tip?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  if (!tip) return <span className={className}>{children}</span>;
  return (
    <HoverTooltip className={className} content={tip}>
      {children}
    </HoverTooltip>
  );
}

function getEventAriaLabel(ev: WeekGridEvent): string {
  const startMin = hhmmToMinutes(ev.startTime);
  const endMin = startMin + ev.duration * SLOT_MINUTES;
  const timeRange = `${minutesToTime(startMin)} a ${minutesToTime(endMin)}`;
  const parts = [
    ev.title || ev.uc || ev.type || "Evento",
    `${WEEKDAY_LABELS_LONG[ev.weekday]}, ${timeRange}`,
  ];
  if (ev.turma) parts.push(`turma ${ev.turma}`);
  if (ev.professor) parts.push(`docente ${ev.professor}`);
  if (ev.sala) parts.push(`sala ${ev.sala}`);
  return parts.join(" — ");
}

interface ScheduleEventCardProps {
  ev: WeekGridEvent;
  /** Grid column (1-based, accounting for time column) where the card starts. */
  startCol: number;
  /** Grid row (1-based) where the card starts. */
  startRow: number;
  /** Column span (in turma columns). */
  colSpan: number;
  /** Row span (in 30-min slots). */
  rowSpan: number;
  /** Lane index when this event shares a column with overlapping events (#24). */
  lane?: number;
  /** Total lanes in this event's cluster; >1 means render side-by-side. */
  laneCount?: number;
  /** Event id shared by this event's segments, set only when it has >1 (#20). */
  arcGroupId?: string;
  /** This segment's order within the event, for arc ordering (#20). */
  arcSegIndex?: number;
  style: SubjectStyle;
  isEditing: boolean;
  /**
   * Compact week range (e.g. "1-7") shown at the bottom when the session runs
   * in only some of the selected weeks. Empty for sessions spanning them all.
   */
  weekRangeLabel?: string;
  onClick?: (event: WeekGridEvent) => void;
}

// Each card fades its bottom edge so clipped text trails off visually instead
// of being abruptly cut. Mask is applied as an inline style because Tailwind
// doesn't have a single-value linear-gradient mask utility.
const FADE_MASK =
  "linear-gradient(to bottom, black calc(100% - 3px), rgba(0,0,0,0.2) calc(100% - 1px), transparent 100%)";

/**
 * One event button in the week grid. Renders the title/type/body lines with
 * marquee scroll on hover/focus and switches to the "being edited" palette
 * when the drawer is open on this card.
 */
export default function ScheduleEventCard({
  ev,
  startCol,
  startRow,
  colSpan,
  rowSpan,
  lane = 0,
  laneCount = 1,
  arcGroupId,
  arcSegIndex,
  style,
  isEditing,
  weekRangeLabel = "",
  onClick,
}: ScheduleEventCardProps) {
  const clickable = !!onClick;
  // A 30-min event (single slot) is too short for the stacked title/type/body
  // lines, so pack the info into two rows: [UC, teacher] / [type, room] (#24).
  const compact = rowSpan === 1;
  const ariaLabel = weekRangeLabel
    ? `${getEventAriaLabel(ev)} — semanas ${weekRangeLabel}`
    : getEventAriaLabel(ev);

  // Hover tooltips (#4): full UC name(s); teacher/room availability grids.
  // The availability bodies only mount when the tooltip opens, so they fetch
  // on hover, not on render.
  const ucNames = ev.subjectNames?.length ? ev.subjectNames : ev.uc ? [ev.uc] : [];
  const ucTip =
    ucNames.length > 0 ? (
      <span className="block font-semibold whitespace-pre-line">{ucNames.join("\n")}</span>
    ) : undefined;
  const roomsTip =
    ev.rooms && ev.rooms.length > 0 ? (
      ev.rooms.length === 1 ? (
        <RoomAvailability roomId={ev.rooms[0]!.id} name={ev.rooms[0]!.name} fill />
      ) : (
        <div className="flex gap-3">
          {ev.rooms.map((room) => (
            <RoomAvailability key={room.id} roomId={room.id} name={room.name} />
          ))}
        </div>
      )
    ) : undefined;
  return (
    <button
      type="button"
      {...{ [SCHEDULE_EVENT_DATA_ATTR]: "" }}
      data-arc-group={arcGroupId}
      data-arc-seg={arcSegIndex}
      data-arc-color={arcGroupId ? style.border : undefined}
      onClick={onClick ? () => onClick(ev) : undefined}
      aria-label={ariaLabel}
      aria-current={isEditing ? "true" : undefined}
      className={`group relative my-[1px] rounded border text-left text-[11px] leading-tight overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C73F24]/70 focus-visible:z-10 ${
        isEditing ? "z-10" : ""
      } ${clickable ? "cursor-pointer hover:brightness-95 transition" : "cursor-default"}`}
      style={{
        gridColumn: `${startCol} / span ${colSpan}`,
        gridRow: `${startRow} / span ${rowSpan}`,
        ...(laneCount > 1
          ? {
              justifySelf: "start",
              width: `calc(100% / ${laneCount})`,
              marginLeft: `calc(100% * ${lane} / ${laneCount})`,
            }
          : null),
        backgroundColor: style.background,
        color: style.text,
        // Editing keeps the subject's own colours and signals selection with a
        // neutral ring that reads against any palette hue (PI ToDo #11).
        borderColor: isEditing ? SUBJECT_SELECTION_RING : style.border,
        boxShadow: isEditing ? `inset 0 0 0 2px ${SUBJECT_SELECTION_RING}` : undefined,
      }}
      disabled={!clickable}
    >
      <div
        className="absolute inset-0 overflow-hidden px-1.5 py-0.5"
        style={{ maskImage: FADE_MASK, WebkitMaskImage: FADE_MASK }}
      >
        {compact ? (
          <div className="flex h-full flex-col justify-center gap-px">
            <div className="flex items-baseline gap-1">
              {ev.title && (
                <Field className="min-w-0 flex-1" tip={ucTip}>
                  <MarqueeText className="font-semibold">{ev.title}</MarqueeText>
                </Field>
              )}
              {ev.type && (
                <MarqueeText className="min-w-0 max-w-[55%] text-[10px] uppercase leading-none opacity-70">
                  {ev.type}
                </MarqueeText>
              )}
            </div>
            <div className="flex items-baseline gap-1">
              {ev.teachers && ev.teachers.length > 0 && (
                <TeacherHoverNames teachers={ev.teachers} className="min-w-0 flex-1" />
              )}
              {ev.sala && (
                <Field className="min-w-0 max-w-[55%]" tip={roomsTip}>
                  <MarqueeText className="opacity-80">{ev.sala}</MarqueeText>
                </Field>
              )}
            </div>
          </div>
        ) : (
          <>
            {ev.title && (
              <Field className="block" tip={ucTip}>
                <MarqueeText className="font-semibold">{ev.title}</MarqueeText>
              </Field>
            )}
            {ev.type && (
              <MarqueeText className="text-[10px] uppercase leading-none opacity-70">
                {ev.type}
              </MarqueeText>
            )}
            {ev.teachers && ev.teachers.length > 0 && (
              <TeacherHoverNames teachers={ev.teachers} className="block" />
            )}
            {ev.rooms && ev.rooms.length > 0 && (
              <Field className="block" tip={roomsTip}>
                <MarqueeText className="opacity-80">
                  {ev.rooms.map((room) => room.name).join(", ")}
                </MarqueeText>
              </Field>
            )}
          </>
        )}
      </div>
      {weekRangeLabel && (
        // Week range pinned to the bottom-right marks a session that only runs
        // in some of the selected weeks. Sits outside the masked content div so
        // the bottom fade doesn't clip it; currentColor tracks the card text.
        <span
          aria-hidden="true"
          title={`Semanas ${weekRangeLabel}`}
          className="pointer-events-none absolute bottom-0 right-0 z-10 px-1 text-[9px] font-semibold leading-tight tabular-nums opacity-80"
        >
          {weekRangeLabel}
        </span>
      )}
    </button>
  );
}
