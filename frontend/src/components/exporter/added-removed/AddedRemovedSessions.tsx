import { EmptyState } from "@/components/exporter/ExportSection";
import type { ProjectExportPayload } from "@/types/exporter";

export default function AddedRemovedSessions({
  data,
}: {
  data: ProjectExportPayload["added_removed_sessions"];
}) {
  const groups = [
    { label: "Adicionadas", rows: data.added, tone: "text-green-700 bg-green-50 border-green-200" },
    { label: "Removidas", rows: data.removed, tone: "text-red-700 bg-red-50 border-red-200" },
  ];

  if (!data.added.length && !data.removed.length) {
    return <EmptyState>Sem aulas adicionadas ou removidas.</EmptyState>;
  }

  return (
    <div className="grid gap-4 p-5 md:grid-cols-2">
      {groups.map((group) => (
        <div key={group.label} className="rounded-lg border border-[#e5e4e7] overflow-hidden">
          <div
            className={`border-b px-4 py-2 text-xs font-bold uppercase tracking-wider ${group.tone}`}
          >
            {group.label} · {group.rows.length}
          </div>
          <div className="max-h-72 overflow-auto">
            {group.rows.map((session) => (
              <div
                key={session.id}
                className="border-b border-[#e5e4e7] px-4 py-2.5 text-sm text-[#08060d] last:border-0"
              >
                <code className="text-xs">{session.id}</code>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
