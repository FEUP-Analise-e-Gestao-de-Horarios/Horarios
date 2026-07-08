import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";
import { X } from "lucide-react";
import { api } from "@/api/client";
import { useProject } from "@/api/hooks/project/project";
import DashboardNavbar from "@/components/dashboard/DashboardNavbar";
import SessionPopup from "@/components/dashboard/SessionPopup";
import WeekGrid, { type WeekGridEvent, type WeekGridMark } from "@/components/dashboard/WeekGrid";
import type { RedBlockBase } from "@/types/project/red_block";
import type { SessionResponse, WeekBlockResponse } from "@/types/project/sessions";
import {
  type DashboardSessionHighlightTone,
  type ExportSessionPreview,
  findTargetWeekBlockIndex,
  parseExportSessionContextIds,
  parseExportSessionPreview,
  parseHighlightedSessionIds,
  parseSessionHighlightTone,
  withExportSessionPreview,
  withExportSessionWeekBlock,
} from "@/utils/exporter/dashboardNavigation";

type ContextKind = "class" | "room" | "teacher";

interface ContextPanelData {
  key: string;
  kind: ContextKind;
  id: string;
  title: string;
  subtitle: string;
  blocks: WeekBlockResponse[];
  redBlocks: RedBlockBase[];
  isLoading: boolean;
  isError: boolean;
}

interface ExportSessionContextResource {
  id: string;
  kind: ContextKind;
  title: string;
  subtitle: string;
  blocks: WeekBlockResponse[];
  red_blocks: RedBlockBase[];
}

interface ExportSessionContextPayload {
  classes: ExportSessionContextResource[];
  rooms: ExportSessionContextResource[];
  teachers: ExportSessionContextResource[];
}

const KIND_LABEL: Record<ContextKind, string> = {
  class: "Turma",
  room: "Sala",
  teacher: "Docente",
};
const FULL_TIMETABLE_WINDOW = { startTime: 800, endTime: 2000 };

interface TimetableLayout {
  allowCardScroll: boolean;
  isPreviewMode: boolean;
  maxHeight: number;
  previewSlotHeight: number;
}

function calculateTimetableLayout(panelCount: number): TimetableLayout {
  if (typeof window === "undefined") {
    return { allowCardScroll: false, isPreviewMode: true, maxHeight: 180, previewSlotHeight: 12 };
  }

  const isPreviewMode = window.innerWidth >= 768;
  if (!isPreviewMode) {
    return {
      allowCardScroll: false,
      isPreviewMode,
      maxHeight: 340,
      previewSlotHeight: 30,
    };
  }

  const rows = Math.max(1, Math.ceil(Math.max(panelCount, 1) / 2));
  const pageChromePx = window.innerWidth >= 1024 ? 166 : 176;
  const cardChromePx = 62;
  const rowGapPx = 12;
  const availableCardHeight = Math.floor(
    (window.innerHeight - pageChromePx - rowGapPx * (rows - 1)) / rows,
  );
  const previewSlotHeight = window.innerWidth >= 1536 ? 16 : window.innerWidth >= 1024 ? 14 : 12;

  return {
    allowCardScroll: false,
    isPreviewMode,
    maxHeight: Math.max(80, availableCardHeight - cardChromePx),
    previewSlotHeight,
  };
}

function useTimetableLayout(panelCount: number): TimetableLayout {
  const [layout, setLayout] = useState(() => calculateTimetableLayout(panelCount));

  useEffect(() => {
    const update = () => setLayout(calculateTimetableLayout(panelCount));
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [panelCount]);

  return layout;
}

function sessionEvents(sessions: SessionResponse[]): WeekGridEvent[] {
  return sessions.map((session) => ({
    id: session.id,
    weekday: session.weekday,
    startTime: session.start_time,
    duration: session.duration,
    title: session.subjects
      .map((subject) => subject.acronym)
      .filter(Boolean)
      .join(", "),
    body: [
      session.teachers
        .map((teacher) => teacher.acronym)
        .filter(Boolean)
        .join(", "),
      session.classes
        .map((classItem) => classItem.code)
        .filter(Boolean)
        .join(", "),
      session.rooms
        .map((room) => room.name)
        .filter(Boolean)
        .join(", "),
    ].filter(Boolean),
    type: session.type,
  }));
}

function redBlockMarks(redBlocks: RedBlockBase[]): WeekGridMark[] {
  return redBlocks.map((block) => ({
    id: block.id,
    weekday: block.weekday,
    time: block.hour,
  }));
}

function hhmmToMinutes(hhmm: number): number {
  return Math.floor(hhmm / 100) * 60 + (hhmm % 100);
}

function slotCountForTimeWindow(timeWindow: { startTime: number; endTime: number }): number {
  const minutes = Math.max(
    30,
    hhmmToMinutes(timeWindow.endTime) - hhmmToMinutes(timeWindow.startTime),
  );
  return Math.max(1, Math.ceil(minutes / 30));
}

function previewSlotHeightFor(
  timeWindow: { startTime: number; endTime: number },
  maxGridHeight: number,
  preferredSlotHeight: number,
): number {
  const gridHeaderHeight = 22;
  const slotCount = slotCountForTimeWindow(timeWindow);
  const fittedHeight = Math.floor((maxGridHeight - gridHeaderHeight) / slotCount);
  return Math.max(4, Math.min(preferredSlotHeight, fittedHeight));
}

function ContextPanel({
  panel,
  targetWeek,
  preview,
  highlightedEventIds,
  highlightedEventTone,
  allowCardScroll,
  isPreviewMode,
  maxGridHeight,
  previewSlotHeight,
  onOpenDetail,
  onSessionClick,
}: {
  panel: ContextPanelData;
  targetWeek: string | null;
  preview: ExportSessionPreview;
  highlightedEventIds: Set<string>;
  highlightedEventTone: DashboardSessionHighlightTone;
  allowCardScroll: boolean;
  isPreviewMode: boolean;
  maxGridHeight: number;
  previewSlotHeight: number;
  onOpenDetail: (panel: ContextPanelData) => void;
  onSessionClick: (session: SessionResponse) => void;
}) {
  const blocks = withExportSessionWeekBlock(panel.blocks, preview);
  const targetBlockIdx = findTargetWeekBlockIndex(blocks, targetWeek);
  const activeBlock = blocks[targetBlockIdx === -1 ? 0 : targetBlockIdx] ?? null;
  const sessions = activeBlock?.sessions ?? [];
  const events = withExportSessionPreview(sessionEvents(sessions), activeBlock, preview);
  const marks = redBlockMarks(panel.redBlocks);
  const timeWindow = FULL_TIMETABLE_WINDOW;
  const fittedSlotHeight = isPreviewMode
    ? previewSlotHeightFor(timeWindow, maxGridHeight, previewSlotHeight)
    : previewSlotHeight;

  return (
    <section className="rounded-lg border border-[#e5e4e7] bg-white shadow-[0_2px_8px_rgba(0,0,0,0.06)] overflow-hidden">
      <div className="border-b border-[#e5e4e7] px-3 py-2 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs font-bold uppercase tracking-wider text-[#6b6375]">
            {KIND_LABEL[panel.kind]}
          </div>
          <h2 className="truncate text-base font-bold text-[#08060d]">{panel.title}</h2>
          {panel.subtitle && (
            <div className="truncate text-sm text-[#6b6375]">{panel.subtitle}</div>
          )}
        </div>
        {panel.isError && (
          <span className="shrink-0 rounded border border-red-200 bg-red-50 px-2 py-1 text-xs font-semibold text-red-700">
            indisponível
          </span>
        )}
      </div>
      <div className="p-2">
        {panel.isLoading ? (
          <div
            className="rounded-lg border border-[#e5e4e7] bg-[#f9f7f4] animate-pulse"
            style={{ height: maxGridHeight }}
          />
        ) : (
          <div
            role={isPreviewMode ? "button" : undefined}
            tabIndex={isPreviewMode ? 0 : undefined}
            className={
              isPreviewMode
                ? "block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8c2d19] focus-visible:ring-offset-2"
                : undefined
            }
            onClick={isPreviewMode ? () => onOpenDetail(panel) : undefined}
            onKeyDown={(event) => {
              if (isPreviewMode && (event.key === "Enter" || event.key === " ")) {
                event.preventDefault();
                onOpenDetail(panel);
              }
            }}
          >
            <WeekGrid
              events={events}
              marks={marks}
              layout={isPreviewMode && allowCardScroll ? "compact" : "natural"}
              maxHeight={maxGridHeight}
              slotHeight={fittedSlotHeight}
              highlightedMinHeight={isPreviewMode ? 18 : 38}
              contentMode={isPreviewMode ? "subject" : "full"}
              density={isPreviewMode ? "preview" : "normal"}
              startTime={timeWindow.startTime}
              endTime={timeWindow.endTime}
              highlightedEventIds={highlightedEventIds}
              highlightedEventTone={highlightedEventTone}
              onEventClick={
                isPreviewMode
                  ? undefined
                  : (event) => {
                      const session = sessions.find((candidate) => candidate.id === event.id);
                      if (session) onSessionClick(session);
                    }
              }
              emptyMessage="Sem aulas nem blocos vermelhos nesta semana."
            />
          </div>
        )}
      </div>
    </section>
  );
}

function TimetableDetailModal({
  panel,
  targetWeek,
  preview,
  highlightedEventIds,
  highlightedEventTone,
  onClose,
}: {
  panel: ContextPanelData;
  targetWeek: string | null;
  preview: ExportSessionPreview;
  highlightedEventIds: Set<string>;
  highlightedEventTone: DashboardSessionHighlightTone;
  onClose: () => void;
}) {
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const blocks = withExportSessionWeekBlock(panel.blocks, preview);
  const targetBlockIdx = findTargetWeekBlockIndex(blocks, targetWeek);
  const activeBlock = blocks[targetBlockIdx === -1 ? 0 : targetBlockIdx] ?? null;
  const sessions = activeBlock?.sessions ?? [];
  const events = withExportSessionPreview(sessionEvents(sessions), activeBlock, preview);
  const marks = redBlockMarks(panel.redBlocks);
  const timeWindow = FULL_TIMETABLE_WINDOW;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[92vh] w-full max-w-[92vw] flex-col overflow-hidden rounded-lg border border-[#d8d3cf] bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-[#e5e4e7] px-5 py-4">
          <div className="min-w-0">
            <div className="text-xs font-bold uppercase tracking-wider text-[#6b6375]">
              {KIND_LABEL[panel.kind]}
            </div>
            <h2 className="truncate text-xl font-bold text-[#08060d]">{panel.title}</h2>
            {panel.subtitle && (
              <div className="truncate text-sm text-[#6b6375]">{panel.subtitle}</div>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-[#d8d3cf] p-2 text-[#6b6375] transition-colors hover:bg-[#f9f7f4] hover:text-[#08060d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#8c2d19]"
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>
        <div className="min-h-0 flex-1 p-4">
          <div className="h-[calc(92vh-128px)] min-h-[420px]">
            <WeekGrid
              events={events}
              marks={marks}
              layout="contained"
              startTime={timeWindow.startTime}
              endTime={timeWindow.endTime}
              highlightedEventIds={highlightedEventIds}
              highlightedEventTone={highlightedEventTone}
              emptyMessage="Sem aulas nem blocos vermelhos nesta semana."
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ExportSessionContextPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [searchParams] = useSearchParams();
  const pid = projectId ?? "";
  const project = useProject(pid);
  const preview = parseExportSessionPreview(searchParams);
  const contextIds = parseExportSessionContextIds(searchParams);
  const highlightedEventIds = parseHighlightedSessionIds(searchParams);
  const highlightedEventTone = parseSessionHighlightTone(searchParams);
  const targetWeek = searchParams.get("week") ?? preview?.week ?? null;
  const [selectedPanel, setSelectedPanel] = useState<ContextPanelData | null>(null);
  const [selectedSession, setSelectedSession] = useState<SessionResponse | null>(null);

  const contextQuery = useQuery({
    queryKey: ["projects", pid, "export-session-context", searchParams.toString()],
    queryFn: () =>
      api.getData<ExportSessionContextPayload>(
        `/api/projects/${pid}/export/session-context?${searchParams.toString()}`,
      ),
    enabled:
      !!pid &&
      !!preview &&
      (contextIds.classIds.length > 0 ||
        contextIds.roomIds.length > 0 ||
        contextIds.teacherIds.length > 0),
  });

  const panels = useMemo<ContextPanelData[]>(() => {
    const data = contextQuery.data;
    if (!data) {
      return [
        ...contextIds.classIds.map((id) => ({
          key: `class-${id}`,
          kind: "class" as const,
          id,
          title: "A carregar...",
          subtitle: KIND_LABEL.class,
          blocks: [],
          redBlocks: [],
          isLoading: contextQuery.isLoading,
          isError: contextQuery.isError,
        })),
        ...contextIds.roomIds.map((id) => ({
          key: `room-${id}`,
          kind: "room" as const,
          id,
          title: "A carregar...",
          subtitle: KIND_LABEL.room,
          blocks: [],
          redBlocks: [],
          isLoading: contextQuery.isLoading,
          isError: contextQuery.isError,
        })),
        ...contextIds.teacherIds.map((id) => ({
          key: `teacher-${id}`,
          kind: "teacher" as const,
          id,
          title: "A carregar...",
          subtitle: KIND_LABEL.teacher,
          blocks: [],
          redBlocks: [],
          isLoading: contextQuery.isLoading,
          isError: contextQuery.isError,
        })),
      ];
    }

    const toPanel = (panel: ExportSessionContextResource): ContextPanelData => ({
      key: `${panel.kind}-${panel.id}`,
      kind: panel.kind,
      id: panel.id,
      title: panel.title,
      subtitle: panel.subtitle,
      blocks: panel.blocks,
      redBlocks: panel.red_blocks,
      isLoading: false,
      isError: false,
    });

    return [
      ...data.classes.map(toPanel),
      ...data.rooms.map(toPanel),
      ...data.teachers.map(toPanel),
    ];
  }, [
    contextIds.classIds,
    contextIds.roomIds,
    contextIds.teacherIds,
    contextQuery.data,
    contextQuery.isError,
    contextQuery.isLoading,
  ]);
  const timetableLayout = useTimetableLayout(panels.length);

  const pageTitle = preview?.title ?? "Aula exportada";
  const toneClass =
    highlightedEventTone === "added"
      ? "border-green-300 bg-green-50 text-green-800"
      : "border-red-300 bg-red-50 text-red-800";

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <title>
        {project.data ? `${pageTitle} · ${project.data.name} · AGH` : `${pageTitle} · AGH`}
      </title>
      <DashboardNavbar projectId={pid} isReady={!!project.data?.ingestion_finished_at} />

      <main
        className={`flex-1 min-h-0 ${timetableLayout.isPreviewMode ? "overflow-hidden" : "overflow-auto"}`}
      >
        <div
          className={`flex h-full w-full flex-col ${
            timetableLayout.isPreviewMode
              ? "px-3 py-3 md:px-4 lg:px-5 xl:px-6 2xl:mx-auto 2xl:max-w-[1500px]"
              : "max-w-7xl mx-auto px-6 py-4"
          }`}
        >
          <div className="mb-2 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="truncate text-xl font-bold text-[#08060d]">{pageTitle}</h1>
              <div className="mt-1 text-sm text-[#6b6375]">
                {targetWeek ? `Semana ${targetWeek}` : "Semana exportada"}
              </div>
            </div>
            <span className={`rounded border px-3 py-1 text-sm font-bold ${toneClass}`}>
              {highlightedEventTone === "added" ? "Aula adicionada" : "Aula removida"}
            </span>
          </div>

          {!preview ? (
            <div className="rounded-lg border border-[#e5e4e7] bg-white p-6 text-sm text-red-600">
              Não foi possível abrir o contexto desta aula exportada.
            </div>
          ) : panels.length === 0 ? (
            <div className="rounded-lg border border-[#e5e4e7] bg-white p-6 text-sm text-[#6b6375]">
              Esta aula exportada não traz salas, docentes ou turmas para contextualizar.
            </div>
          ) : (
            <div className="grid flex-1 content-start gap-3 pb-3 md:grid-cols-2">
              {panels.map((panel) => (
                <ContextPanel
                  key={panel.key}
                  panel={panel}
                  targetWeek={targetWeek}
                  preview={preview}
                  highlightedEventIds={highlightedEventIds}
                  highlightedEventTone={highlightedEventTone}
                  allowCardScroll={timetableLayout.allowCardScroll}
                  isPreviewMode={timetableLayout.isPreviewMode}
                  maxGridHeight={timetableLayout.maxHeight}
                  previewSlotHeight={timetableLayout.previewSlotHeight}
                  onOpenDetail={setSelectedPanel}
                  onSessionClick={setSelectedSession}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {selectedPanel && preview && (
        <TimetableDetailModal
          panel={selectedPanel}
          targetWeek={targetWeek}
          preview={preview}
          highlightedEventIds={highlightedEventIds}
          highlightedEventTone={highlightedEventTone}
          onClose={() => setSelectedPanel(null)}
        />
      )}

      {selectedSession && (
        <SessionPopup
          session={selectedSession}
          projectId={pid}
          onClose={() => setSelectedSession(null)}
        />
      )}
    </div>
  );
}
