import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useProject, useProjectRoom } from "@/api/hooks/useDashboard";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";
import SessionPopup from "@/components/dashboard/SessionPopup";
import WeekGrid, { type WeekGridEvent, type WeekGridMark } from "@/components/dashboard/WeekGrid";
import type { RedBlockBase, SessionResponse } from "@/types/dashboard";

interface WeekBlock {
  signature: string;
  weeks: string[];
  sessions: SessionResponse[];
}

function sessionsSignature(sessions: SessionResponse[]): string {
  return sessions
    .map((s) => `${s.weekday}|${s.start_time}|${s.duration}|${s.original_block_id}`)
    .sort()
    .join(";");
}

function groupIntoBlocks(sessions: SessionResponse[]): WeekBlock[] {
  const byWeek = new Map<string, SessionResponse[]>();
  for (const s of sessions) {
    const arr = byWeek.get(s.week);
    if (arr) arr.push(s);
    else byWeek.set(s.week, [s]);
  }
  const sortedWeeks = [...byWeek.keys()].sort();

  const blocks: WeekBlock[] = [];
  for (const week of sortedWeeks) {
    const weekSessions = byWeek.get(week) ?? [];
    const signature = sessionsSignature(weekSessions);
    const last = blocks[blocks.length - 1];
    if (last && last.signature === signature) {
      last.weeks.push(week);
    } else {
      blocks.push({ signature, weeks: [week], sessions: weekSessions });
    }
  }
  return blocks;
}

function formatShortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-PT", { day: "2-digit", month: "short" });
}

function formatBlockLabel(block: WeekBlock): string {
  const first = block.weeks[0];
  const last = block.weeks[block.weeks.length - 1];
  if (!first) return "—";
  const count = block.weeks.length;
  const range =
    count === 1 || !last
      ? formatShortDate(first)
      : `${formatShortDate(first)} – ${formatShortDate(last)}`;
  const weeksLabel = count === 1 ? "1 semana" : `${count} semanas`;
  return `${range} · ${weeksLabel}`;
}

export default function RoomDetailPage() {
  const { projectId, roomId } = useParams<{ projectId: string; roomId: string }>();
  const pid = projectId ?? "";
  const rid = roomId ?? "";

  const project = useProject(pid);
  const { data, isLoading, isError } = useProjectRoom(pid, rid);

  const blocks = useMemo(() => (data ? groupIntoBlocks(data.sessions) : []), [data]);
  const [selectedBlockIdx, setSelectedBlockIdx] = useState(0);
  const [selectedSession, setSelectedSession] = useState<SessionResponse | null>(null);
  const [prevRid, setPrevRid] = useState(rid);
  if (rid !== prevRid) {
    setPrevRid(rid);
    setSelectedSession(null);
    setSelectedBlockIdx(0);
  }

  const activeBlock = blocks[selectedBlockIdx] ?? blocks[0] ?? null;
  const blockSessions: SessionResponse[] = activeBlock?.sessions ?? [];

  const events: WeekGridEvent[] = blockSessions.map((s) => ({
    id: s.id,
    weekday: s.weekday,
    startTime: s.start_time,
    duration: s.duration,
    title: s.subjects.map((x) => x.acronym).join(", "),
    body: [
      s.teachers.map((t) => t.acronym).join(", "),
      s.classes.map((c) => c.code).join(", "),
    ].filter((line) => line.length > 0),
    type: s.type,
  }));

  const redBlocks: RedBlockBase[] = data?.red_blocks ?? [];
  const marks: WeekGridMark[] = redBlocks.map((rb) => ({
    id: rb.id,
    weekday: rb.weekday,
    time: rb.hour,
  }));

  const handleEventClick = (ev: WeekGridEvent) => {
    const session = blockSessions.find((s) => s.id === ev.id);
    if (session) setSelectedSession(session);
  };

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

              <div className="flex items-center justify-between gap-3 flex-wrap">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-[#08060d]">
                  Horário
                </h2>
                {blocks.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {blocks.map((b, i) => {
                      const active = i === selectedBlockIdx;
                      return (
                        <button
                          key={b.signature + i}
                          type="button"
                          onClick={() => setSelectedBlockIdx(i)}
                          className={`text-sm rounded-md px-3 py-1 border transition-colors ${
                            active
                              ? "bg-[#8c2d19] text-white border-[#8c2d19]"
                              : "bg-white text-[#08060d] border-[#e5e4e7] hover:bg-[#f9f7f4]"
                          }`}
                        >
                          {formatBlockLabel(b)}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className="flex-1 min-h-0">
                <WeekGrid
                  events={events}
                  marks={marks}
                  onEventClick={handleEventClick}
                  emptyMessage="Sem aulas nem blocos vermelhos para esta sala."
                />
              </div>
            </>
          )}
        </div>
      </div>

      {selectedSession && (
        <SessionPopup
          session={selectedSession}
          projectId={pid}
          currentRoomId={rid}
          onClose={() => setSelectedSession(null)}
        />
      )}
    </div>
  );
}
