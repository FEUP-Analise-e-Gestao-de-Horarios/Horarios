import type { ProjectExportPayload } from "@/types/exporter";

function StatCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: string;
}) {
  const toneClasses =
    tone === "warning"
      ? "text-amber-700 bg-amber-50 border-amber-200"
      : tone === "danger"
        ? "text-red-700 bg-red-50 border-red-200"
        : "text-[#08060d] bg-white border-[#e5e4e7]";

  return (
    <div
      className={`rounded-lg border px-3 py-2 shadow-[0_2px_8px_rgba(0,0,0,0.04)] ${toneClasses}`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider opacity-75">{label}</p>
      <p className="text-xl font-bold leading-tight">{value}</p>
    </div>
  );
}

export default function ExporterStats({
  data,
  totalConflicts,
}: {
  data: ProjectExportPayload;
  totalConflicts: number;
}) {
  const changedBlocks = data.modification_steps.length;

  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
      <StatCard label="Passos" value={data.modification_steps.length} />
      <StatCard label="Alterações" value={changedBlocks} />
      <StatCard label="Adicionadas" value={data.added_removed_sessions.added.length} />
      <StatCard label="Removidas" value={data.added_removed_sessions.removed.length} />
      <StatCard
        label="Conflitos"
        value={totalConflicts}
        tone={totalConflicts ? "danger" : "neutral"}
      />
    </div>
  );
}
