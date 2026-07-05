import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useProject } from "@/api/hooks/project/project";
import { useProjectRoom } from "@/api/hooks/project/room";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";
import SessionPopup from "@/components/dashboard/SessionPopup";
import WeekGrid, { type WeekGridEvent, type WeekGridMark } from "@/components/dashboard/WeekGrid";
import type { RedBlockBase } from "@/types/project/red_block";
import type { SessionResponse, WeekBlockResponse } from "@/types/project/sessions";
import { formatBlockLabel } from "@/utils/date";
import {
  findTargetWeekBlockIndex,
  parseConflictSessionIds,
  parseConflictWeeks,
  weekBlockButtonClass,
  weekBlockHasConflict,
} from "@/utils/exporter/dashboardNavigation";

export default function RoomDetailPage() {
  const { projectId, roomId } = useParams<{ projectId: string; roomId: string }>();
  const [searchParams] = useSearchParams();
  const pid = projectId ?? "";
  const rid = roomId ?? "";
  const targetWeek = searchParams.get("week");
  const highlightedEventIds = parseConflictSessionIds(searchParams);
  const conflictWeeks = parseConflictWeeks(searchParams);

  const project = useProject(pid);
  const { data, isLoading, isError } = useProjectRoom(pid, rid);

  const blocks: WeekBlockResponse[] = data?.blocks ?? [];
  const targetBlockIdx = findTargetWeekBlockIndex(blocks, targetWeek);
  const [selectedBlockIdx, setSelectedBlockIdx] = useState(0);
  const [selectedSession, setSelectedSession] = useState<SessionResponse | null>(null);
  const [prevRid, setPrevRid] = useState(rid);
  const [appliedTargetWeek, setAppliedTargetWeek] = useState<string | null>(null);
  if (rid !== prevRid) {
    setPrevRid(rid);
    setAppliedTargetWeek(null);
    setSelectedSession(null);
    setSelectedBlockIdx(0);
  }
  if (targetWeek && targetBlockIdx !== -1 && targetWeek !== appliedTargetWeek) {
    setAppliedTargetWeek(targetWeek);
    setSelectedBlockIdx(targetBlockIdx);
  }

  const activeBlock = blocks[selectedBlockIdx] ?? blocks[0] ?? null;
  const blockSessions: SessionResponse[] = activeBlock?.sessions ?? [];

  const totalSessions = blocks.reduce((sum, b) => sum + b.sessions.length * b.weeks.length, 0);

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

  const title = isError
    ? "Erro · AGH"
    : data && project.data
      ? `${data.name} · ${project.data.name} · AGH`
      : "A carregar… · AGH";

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <title>{title}</title>
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
              <div
                data-copy-id={rid}
                data-copy-label="ID da sala"
                className="bg-white rounded-lg border border-[#e5e4e7] shadow-[0_2px_8px_rgba(0,0,0,0.06)] px-6 py-4 flex items-start justify-between gap-4"
              >
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
                    <span className="font-semibold text-[#08060d]">{totalSessions}</span> aulas
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
                      const hasConflictWeek = weekBlockHasConflict(b, conflictWeeks);
                      return (
                        <button
                          key={b.weeks[0] ?? i}
                          type="button"
                          onClick={() => setSelectedBlockIdx(i)}
                          className={`text-sm rounded-md px-3 py-1 border transition-colors ${weekBlockButtonClass(
                            active,
                            hasConflictWeek,
                          )}`}
                          title={
                            hasConflictWeek ? "Esta semana também tem este conflito" : undefined
                          }
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
                  highlightedEventIds={highlightedEventIds}
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
