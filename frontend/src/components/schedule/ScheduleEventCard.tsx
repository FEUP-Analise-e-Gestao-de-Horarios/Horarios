import type { WeekGridEvent } from "./WeekGrid";
import { SCHEDULE_EVENT_DATA_ATTR } from "./dismissable";
import MarqueeText from "./MarqueeText";
import type { SubjectStyle } from "./subjectColors";

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
  style: SubjectStyle;
  isEditing: boolean;
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
  style,
  isEditing,
  onClick,
}: ScheduleEventCardProps) {
  const clickable = !!onClick;
  return (
    <button
      type="button"
      {...{ [SCHEDULE_EVENT_DATA_ATTR]: "" }}
      onClick={onClick ? () => onClick(ev) : undefined}
      className={`group relative my-[1px] rounded border text-left text-[11px] leading-tight overflow-hidden ${
        isEditing
          ? "bg-[#250902] border-[#38040e] text-white"
          : `${style.bg} ${style.border} ${style.text}`
      } ${clickable ? "cursor-pointer hover:brightness-95 transition" : "cursor-default"}`}
      style={{
        gridColumn: `${startCol} / span ${colSpan}`,
        gridRow: `${startRow} / span ${rowSpan}`,
      }}
      title={ev.title}
      disabled={!clickable}
    >
      <div
        className="absolute inset-0 overflow-hidden px-1.5 py-1"
        style={{ maskImage: FADE_MASK, WebkitMaskImage: FADE_MASK }}
      >
        {ev.title && <MarqueeText className="font-semibold">{ev.title}</MarqueeText>}
        {ev.type && (
          <MarqueeText className="text-[10px] uppercase leading-none opacity-70">
            {ev.type}
          </MarqueeText>
        )}
        {ev.body?.map((line, i) => (
          <MarqueeText key={i} className="opacity-80">
            {line}
          </MarqueeText>
        ))}
      </div>
    </button>
  );
}
