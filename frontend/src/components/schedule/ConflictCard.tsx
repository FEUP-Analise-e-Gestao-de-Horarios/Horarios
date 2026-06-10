import type { ConflictRecord } from "@/types/project/conflicts";

type ConflictCardVariant = "compact" | "full";

interface ConflictCardProps {
  conflict: ConflictRecord;
  /**
   * "full" is the conflicts-drawer presentation: more padding/font-size, and
   * the meta line includes the turma. "compact" is the edit-drawer one: the
   * user is already focused on a single event so the turma is redundant.
   */
  variant?: ConflictCardVariant;
}

const STYLES: Record<
  ConflictCardVariant,
  {
    card: string;
    title: string;
    titleGap: string;
    meta: string;
    reasonsWrap: string;
    reason: string;
  }
> = {
  compact: {
    card: "border-l-3 border-white/30 bg-white/5 rounded p-2 space-y-1.5 text-xs",
    title: "text-white/90 font-semibold",
    titleGap: "space-y-0.5",
    meta: "text-white/70",
    reasonsWrap: "space-y-0.5 pt-1 border-t border-white/10",
    reason: "text-white/80 flex items-start gap-1",
  },
  full: {
    card: "border-l-4 border-white/30 bg-white/5 rounded p-3 space-y-2",
    title: "text-sm font-semibold text-white",
    titleGap: "space-y-1",
    meta: "text-xs text-white/70 mt-1",
    reasonsWrap: "space-y-1 pt-2 border-t border-white/10",
    reason: "text-xs text-white/80 flex items-start gap-2",
  },
};

export default function ConflictCard({ conflict, variant = "full" }: ConflictCardProps) {
  const style = STYLES[variant];
  const metaLine =
    variant === "full"
      ? `${conflict.day} às ${conflict.time} — Turma: ${conflict.turma}`
      : `${conflict.day} · ${conflict.time}`;

  return (
    <div className={style.card}>
      <div className={`${style.title} ${style.titleGap}`}>
        {conflict.event_names.map((name, idx) => (
          <p key={idx} className="line-clamp-1">
            {name}
          </p>
        ))}
      </div>
      <p className={style.meta}>{metaLine}</p>
      <div className={style.reasonsWrap}>
        {conflict.conflict_reasons.map((reason, idx) => (
          <p key={idx} className={style.reason}>
            <span className="text-white/60 flex-shrink-0">•</span>
            <span>{reason}</span>
          </p>
        ))}
      </div>
    </div>
  );
}
