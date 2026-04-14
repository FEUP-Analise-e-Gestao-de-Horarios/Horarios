import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useProject, useProjectRoom } from "@/api/hooks/useDashboard";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";
import WeekGrid, { type WeekGridEvent, type WeekGridMark } from "@/components/dashboard/WeekGrid";
import type { RedBlockDetail, SessionDetail } from "@/types/dashboard";

function formatWeek(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("pt-PT", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function groupByWeek(sessions: SessionDetail[]): Map<string, SessionDetail[]> {
  const map = new Map<string, SessionDetail[]>();
  for (const s of sessions) {
    const existing = map.get(s.week);
    if (existing) existing.push(s);
    else map.set(s.week, [s]);
  }
  return new Map([...map.entries()].sort(([a], [b]) => a.localeCompare(b)));
}

export default function RoomDetailPage() {
  const { projectId, roomId } = useParams<{ projectId: string; roomId: string }>();
  const pid = projectId ?? "";
  const rid = roomId ?? "";

  const project = useProject(pid);
  const { data, isLoading, isError } = useProjectRoom(pid, rid);

  const weeks = useMemo<Map<string, SessionDetail[]>>(
    () => (data ? groupByWeek(data.sessions) : new Map<string, SessionDetail[]>()),
    [data],
  );
  const weekKeys = useMemo(() => [...weeks.keys()], [weeks]);
  const [selectedWeek, setSelectedWeek] = useState<string | null>(null);

  const activeWeek = selectedWeek ?? weekKeys[0] ?? null;
  const weekSessions: SessionDetail[] = activeWeek ? (weeks.get(activeWeek) ?? []) : [];

  const events: WeekGridEvent[] = weekSessions.map((s) => ({
    id: s.id,
    weekday: s.weekday,
    startTime: s.start_time,
    duration: s.duration,
    type: s.type,
  }));

  const redBlocks: RedBlockDetail[] = data?.red_blocks ?? [];
  const marks: WeekGridMark[] = redBlocks.map((rb) => ({
    id: rb.id,
    weekday: rb.weekday,
    time: rb.hour,
  }));

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <DashboardNavbar projectId={pid} isReady={!!project.data?.ingestion_finished_at} />

      <div className="flex-1 min-h-0 overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 pt-6 pb-6 h-full flex flex-col gap-5">
          {isLoading ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 h-32 animate-pulse" />
          ) : isError || !data ? (
            <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] p-6 text-sm text-red-600">
              Erro ao carregar sala.
            </div>
          ) : (
            <>
              <div className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] px-6 py-4 flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h1 className="text-2xl font-bold text-[#08060d]">{data.name}</h1>
                  <div className="mt-1 text-sm text-[#6b6375]">
                    {[data.type, data.size, data.seats && `${data.seats} lugares`]
                      .filter(Boolean)
                      .join(" · ") || "—"}
                  </div>
                </div>
                <div className="shrink-0 text-right text-sm text-[#6b6375]">
                  <div>
                    <span className="font-semibold text-[#08060d]">{data.sessions.length}</span>{" "}
                    aulas
                  </div>
                  <div>
                    <span className="font-semibold text-[#08060d]">{data.red_blocks.length}</span>{" "}
                    blocos vermelhos
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-[#08060d]">
                  Horário
                </h2>
                {weekKeys.length > 0 && (
                  <label className="flex items-center gap-2">
                    <span className="text-xs text-[#6b6375]">Semana</span>
                    <select
                      value={activeWeek ?? ""}
                      onChange={(e) => setSelectedWeek(e.target.value)}
                      className="text-sm bg-white border border-[#e5e4e7] rounded-md px-2 py-1 text-[#08060d] focus:outline-none focus:border-[#8c2d19]"
                    >
                      {weekKeys.map((w) => (
                        <option key={w} value={w}>
                          {formatWeek(w)}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>

              <div className="flex-1 min-h-0">
                <WeekGrid
                  events={events}
                  marks={marks}
                  emptyMessage="Sem aulas nem blocos vermelhos para esta sala."
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
