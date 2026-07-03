import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight } from "lucide-react";
import { useParallelSessions } from "@/api/hooks/useParallelSessions";
import { DAY_ORDER, type ParallelCandidateGraph } from "@/types/parallelSessions";
import ParallelGraph from "@/components/parallel/ParallelGraph";

const DAY_CONFIG: Record<string, { short: string; bg: string; text: string }> = {
  monday: { short: "SEG", bg: "bg-blue-500", text: "text-white" },
  tuesday: { short: "TER", bg: "bg-emerald-500", text: "text-white" },
  wednesday: { short: "QUA", bg: "bg-violet-500", text: "text-white" },
  thursday: { short: "QUI", bg: "bg-orange-500", text: "text-white" },
  friday: { short: "SEX", bg: "bg-rose-500", text: "text-white" },
  saturday: { short: "SAB", bg: "bg-gray-500", text: "text-white" },
};

const SESSION_TYPE_CONFIG: Record<string, { bg: string; text: string }> = {
  TP: { bg: "bg-blue-100", text: "text-blue-700" },
  OT: { bg: "bg-violet-100", text: "text-violet-700" },
  PL: { bg: "bg-emerald-100", text: "text-emerald-700" },
  T: { bg: "bg-orange-100", text: "text-orange-700" },
  S: { bg: "bg-rose-100", text: "text-rose-700" },
};
const SESSION_TYPE_DEFAULT = { bg: "bg-gray-100", text: "text-gray-600" };

/** Stable empty selection so the graph panel keeps a referentially-stable prop. */
const EMPTY_SELECTION: Set<string> = new Set();

function sessionTypeStyle(type: string): { bg: string; text: string } {
  return SESSION_TYPE_CONFIG[type] ?? SESSION_TYPE_DEFAULT;
}

function dayConfig(weekday: string) {
  return DAY_CONFIG[weekday] ?? { short: "?", bg: "bg-gray-400", text: "text-white" };
}

function formatTime(t: number): string {
  const s = String(t).padStart(4, "0");
  return `${s.slice(0, 2)}:${s.slice(2)}`;
}

function graphStartTime(graph: ParallelCandidateGraph): number {
  return graph.nodes[0]?.session.start_time ?? 0;
}

function CandidatesLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-40 rounded-2xl bg-[#e8e8e8] animate-pulse" />
      ))}
    </div>
  );
}

export default function ParallelClassesPage() {
  // The candidate whose graph is shown in the top-right panel.
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  // The subject whose candidates are listed in the left column.
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);

  // Horizontal scroll container of the selected-groups panel and the active
  // subject's column within it, so selecting a subject scrolls it into view.
  const groupsPanelRef = useRef<HTMLDivElement | null>(null);
  const groupsScrollRef = useRef<HTMLDivElement | null>(null);
  const activeGroupColRef = useRef<HTMLDivElement | null>(null);

  // The group card currently playing its "look here" pulse, plus per-card refs
  // so we can scroll the matching card into view.
  const [highlightedGroupId, setHighlightedGroupId] = useState<string | null>(null);
  const groupCardRefs = useRef(new Map<string, HTMLDivElement>());
  const highlightTimer = useRef<number | null>(null);
  useEffect(() => () => window.clearTimeout(highlightTimer.current ?? undefined), []);

  const {
    degrees,
    loadingDegrees,
    degreesError,
    selectedDegree,
    loadingYears,
    yearsError,
    selectedYearIds,
    yearsWithCandidates,
    loadingCandidates,
    candidatesError,
    visibleGraphs,
    assignedBlockIds,
    selectionByGroup,
    isSelectionValid,
    canGroupAll,
    groupViewsBySubject,
    savedGroupIds,
    saving,
    saveStatus,
    showUnsavedModal,
    setShowUnsavedModal,
    showResetModal,
    setShowResetModal,
    handleDegreeClick,
    handleYearSelect,
    handleToggleNode,
    handleCreateGroup,
    handleGroupAll,
    handleRemoveGroup,
    handleBack,
    handleNavigateHome,
    handleSave,
    handleSaveAndExit,
    handleExitWithoutSaving,
    handleReset,
    confirmReset,
  } = useParallelSessions();

  // Group the visible candidate components by subject, sorted for display.
  const graphsBySubject = useMemo(() => {
    const map = new Map<string, ParallelCandidateGraph[]>();
    for (const g of visibleGraphs) {
      const key = g.subject.name;
      const list = map.get(key);
      if (list) list.push(g);
      else map.set(key, [g]);
    }
    for (const list of map.values()) {
      list.sort(
        (a, b) =>
          (DAY_ORDER[a.weekday] ?? 99) - (DAY_ORDER[b.weekday] ?? 99) ||
          graphStartTime(a) - graphStartTime(b),
      );
    }
    return map;
  }, [visibleGraphs]);

  // Degrees for the left-column selector, alphabetically sorted by acronym.
  const sortedDegrees = useMemo(
    () => [...degrees].sort((a, b) => a.acronym.localeCompare(b.acronym)),
    [degrees],
  );

  // Subjects available in the left-column selector, alphabetically sorted.
  const subjectNames = useMemo(
    () => [...graphsBySubject.keys()].sort((a, b) => a.localeCompare(b)),
    [graphsBySubject],
  );

  // Full subject name -> acronym, for the compact selector pills.
  const subjectAcronyms = useMemo(() => {
    const map = new Map<string, string>();
    for (const g of visibleGraphs) map.set(g.subject.name, g.subject.acronym);
    return map;
  }, [visibleGraphs]);

  // Resolve the effective subject: honour the user's pick when it still exists,
  // otherwise fall back to the first one (e.g. after a degree/year change).
  const activeSubject =
    selectedSubject && subjectNames.includes(selectedSubject)
      ? selectedSubject
      : (subjectNames[0] ?? null);

  const subjectGraphs = activeSubject ? (graphsBySubject.get(activeSubject) ?? []) : [];

  // On subject change, jump the panel back to the top and bring the active
  // subject's column into horizontal view.
  useEffect(() => {
    groupsPanelRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    const container = groupsScrollRef.current;
    const col = activeGroupColRef.current;
    if (!container || !col) return;
    const cRect = container.getBoundingClientRect();
    const colRect = col.getBoundingClientRect();
    const delta = colRect.left - cRect.left;
    const target = container.scrollLeft + delta - (container.clientWidth - colRect.width) / 2;
    container.scrollTo({ left: Math.max(0, target), behavior: "smooth" });
  }, [activeSubject]);

  // Block id -> the id of the (shown) group it belongs to, for reveal-on-tap.
  const groupIdByBlock = useMemo(() => {
    const map = new Map<string, string>();
    for (const items of groupViewsBySubject.values())
      for (const view of items) for (const b of view.blocks) map.set(b.blockId, view.group.id);
    return map;
  }, [groupViewsBySubject]);

  // Candidate id -> ids of the groups already carved out of it.
  const groupIdsByCandidate = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const items of groupViewsBySubject.values())
      for (const view of items) {
        const arr = map.get(view.group.candidateGroupId);
        if (arr) arr.push(view.group.id);
        else map.set(view.group.candidateGroupId, [view.group.id]);
      }
    return map;
  }, [groupViewsBySubject]);

  // Scroll a group card into view and play its one-shot "look here" pulse.
  const revealGroup = useCallback((groupId: string) => {
    const el = groupCardRefs.current.get(groupId);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    window.clearTimeout(highlightTimer.current ?? undefined);
    // Clear any current highlight, then start the pulse only after the smooth
    // scroll has had time to land — otherwise it can finish before the card is
    // on screen. Clearing first also restarts the CSS animation on a repeat.
    setHighlightedGroupId(null);
    highlightTimer.current = window.setTimeout(() => {
      setHighlightedGroupId(groupId);
      highlightTimer.current = window.setTimeout(() => setHighlightedGroupId(null), 800);
    }, 380);
  }, []);

  // Tap on an already-grouped node reveals the group it belongs to.
  const handleRevealGroup = useCallback(
    (blockId: string) => {
      const groupId = groupIdByBlock.get(blockId);
      if (groupId) revealGroup(groupId);
    },
    [groupIdByBlock, revealGroup],
  );

  // Selecting a candidate that already has exactly one group jumps to it.
  useEffect(() => {
    if (!selectedCandidateId) return;
    const ids = groupIdsByCandidate.get(selectedCandidateId);
    if (ids && ids.length === 1) revealGroup(ids[0]!);
    // Only react to the candidate selection itself, not later group edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCandidateId]);

  // The single selected year driving the candidate list.
  const activeYearId = yearsWithCandidates.find((y) => selectedYearIds.has(y.id))?.id ?? null;

  // The candidate currently driving the graph panel. Derived from visibleGraphs
  // so a filter change that hides it collapses the panel to its empty state.
  const selectedGraph =
    (selectedCandidateId &&
      visibleGraphs.find((g) => g.candidate_group_id === selectedCandidateId)) ||
    null;
  const selectedSelection = selectedGraph
    ? (selectionByGroup[selectedGraph.candidate_group_id] ?? EMPTY_SELECTION)
    : EMPTY_SELECTION;
  const selectedValid = selectedGraph ? isSelectionValid(selectedGraph.candidate_group_id) : false;
  const selectedDay = selectedGraph ? dayConfig(selectedGraph.weekday) : null;
  const selectedAllAssigned = selectedGraph
    ? selectedGraph.nodes.every((n) => assignedBlockIds.has(n.original_block_id))
    : false;
  const selectedCanGroupAll = selectedGraph ? canGroupAll(selectedGraph.candidate_group_id) : false;
  const selectedUnassignedCount = selectedGraph
    ? selectedGraph.nodes.filter((n) => !assignedBlockIds.has(n.original_block_id)).length
    : 0;

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <header className="shrink-0 sticky top-0 z-50 px-6 py-3 bg-[#1e2028] flex items-center gap-2 w-full flex-wrap border-b border-gray-700">
        <button
          onClick={handleNavigateHome}
          className="bg-[#8c2d19] text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#a33520] transition-colors cursor-pointer"
        >
          Início
        </button>
        <button
          onClick={handleBack}
          className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 transition-colors hover:border-gray-400 hover:bg-white/5 cursor-pointer"
        >
          Horário
        </button>

        <div className="ml-auto flex items-center gap-2">
          {saveStatus && (
            <span
              className={`text-xs font-semibold ${saveStatus.type === "success" ? "text-green-400" : "text-red-400"}`}
            >
              {saveStatus.message}
            </span>
          )}
          <button
            onClick={handleReset}
            disabled={saving}
            className="bg-transparent text-red-400 font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            Recomeçar
          </button>
          <button
            onClick={() => void handleSave()}
            disabled={saving}
            className="bg-transparent text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-gray-600 hover:border-gray-400 hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {saving ? "A guardar..." : "Guardar"}
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-7xl mx-auto px-6 py-6 flex gap-6">
          {/* Left column: degree/year/subject selectors + candidates */}
          <div className="w-[360px] shrink-0 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-3 shrink-0">
              <h2 className="font-bold text-[#333] text-base">Candidatos a paralelas</h2>
            </div>

            {/* Degree selector */}
            {degreesError ? (
              <p className="mb-3 shrink-0 text-xs text-red-600">{degreesError}</p>
            ) : (
              sortedDegrees.length > 0 && (
                <div className="mb-3 shrink-0">
                  <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-[#999]">
                    Curso
                  </p>
                  <div className="flex flex-wrap gap-2 max-h-28 overflow-y-auto pr-1 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                    {sortedDegrees.map((degree) => {
                      const isActive = selectedDegree?.id === degree.id;
                      return (
                        <button
                          key={degree.id}
                          type="button"
                          disabled={loadingDegrees}
                          onClick={() => handleDegreeClick(degree)}
                          className={`rounded-full border px-3 py-1.5 text-[12px] font-semibold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                            isActive
                              ? "border-[#b45309] bg-[#b45309] text-white"
                              : "border-[#e8e8e8] bg-white text-[#555] hover:border-[#d4d4d4] hover:bg-[#faf7f4]"
                          }`}
                        >
                          {degree.acronym}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )
            )}

            {selectedDegree && (
              <>
                <div className="mb-3 shrink-0 border-t border-[#e8e8e8]" />

                {/* Year selector */}
                {yearsError ? (
                  <p className="mb-3 shrink-0 text-xs text-red-600">{yearsError}</p>
                ) : (
                  yearsWithCandidates.length > 0 && (
                    <div className="mb-3 shrink-0">
                      <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-[#999]">
                        Ano
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {yearsWithCandidates.map((year) => {
                          const isActive = activeYearId === year.id;
                          return (
                            <button
                              key={year.id}
                              type="button"
                              disabled={loadingYears}
                              onClick={() => handleYearSelect(year.id)}
                              className={`rounded-full border px-3 py-1.5 text-[12px] font-semibold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                                isActive
                                  ? "border-[#1e2028] bg-[#1e2028] text-white"
                                  : "border-[#e8e8e8] bg-white text-[#555] hover:border-[#d4d4d4] hover:bg-[#faf7f4]"
                              }`}
                            >
                              {year.number}º Ano
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )
                )}

                {subjectNames.length > 0 && (
                  <>
                    <div className="mb-3 shrink-0 border-t border-[#e8e8e8]" />
                    <div className="mb-3 shrink-0">
                      <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-[#999]">
                        Cadeira
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {subjectNames.map((name) => {
                          const isActive = activeSubject === name;
                          return (
                            <button
                              key={name}
                              type="button"
                              onClick={() => setSelectedSubject(name)}
                              className={`rounded-full border px-3 py-1.5 text-[12px] font-semibold transition-colors cursor-pointer ${
                                isActive
                                  ? "border-[#8c2d19] bg-[#8c2d19] text-white"
                                  : "border-[#e8e8e8] bg-white text-[#555] hover:border-[#d4d4d4] hover:bg-[#faf7f4]"
                              }`}
                            >
                              {subjectAcronyms.get(name) ?? name}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </>
                )}

                <div className="mb-3 shrink-0 border-t border-[#e8e8e8]" />
              </>
            )}
            <div className="flex-1 overflow-y-auto pb-6 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
              {loadingCandidates ? (
                <CandidatesLoadingSkeleton />
              ) : candidatesError ? (
                <p className="text-sm text-red-600">{candidatesError}</p>
              ) : graphsBySubject.size === 0 ? (
                <p className="text-sm text-[#aaa]">
                  {selectedDegree ? "Sem aulas em paralelo." : "Seleciona um curso para começar."}
                </p>
              ) : (
                <div className="overflow-hidden rounded-2xl border border-[#e8e8e8] shadow-sm bg-white">
                  {activeSubject && (
                    <div className="px-4 py-2.5 bg-[#fafafa] border-b border-[#e8e8e8]">
                      <p className="font-semibold text-[#222] text-sm">{activeSubject}</p>
                    </div>
                  )}
                  <div className="flex flex-col divide-y divide-[#f0f0f0]">
                    {subjectGraphs.map((graph) => {
                      const day = dayConfig(graph.weekday);
                      const selection =
                        selectionByGroup[graph.candidate_group_id] ?? EMPTY_SELECTION;
                      const allAssigned = graph.nodes.every((n) =>
                        assignedBlockIds.has(n.original_block_id),
                      );
                      const isSelected = selectedCandidateId === graph.candidate_group_id;
                      return (
                        <button
                          key={graph.candidate_group_id}
                          type="button"
                          onClick={() =>
                            setSelectedCandidateId(isSelected ? null : graph.candidate_group_id)
                          }
                          className={`flex w-full items-center gap-2 border-l-2 px-4 py-3 text-left transition-colors cursor-pointer ${
                            isSelected
                              ? "border-l-[#8c2d19] bg-[#8c2d19]/10"
                              : "border-l-transparent hover:bg-[#faf7f4]"
                          }`}
                        >
                          <span
                            className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md ${day.bg} ${day.text}`}
                          >
                            {day.short}
                          </span>
                          <span className="font-bold text-[#333] tabular-nums text-sm">
                            {formatTime(graphStartTime(graph))}
                          </span>
                          <div className="ml-auto flex items-center gap-2">
                            {selection.size > 0 && (
                              <span className="text-[11px] text-amber-600 font-semibold">
                                {selection.size} sel.
                              </span>
                            )}
                            {allAssigned && (
                              <span className="text-[11px] text-emerald-600 font-semibold">
                                Agrupadas
                              </span>
                            )}
                            <span className="text-[11px] text-[#aaa]">
                              {graph.nodes.length} aulas
                            </span>
                            <ChevronRight
                              className={`w-4 h-4 shrink-0 transition-colors ${isSelected ? "text-[#8c2d19]" : "text-[#ccc]"}`}
                            />
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right column: graph (top) + selected groups (bottom) */}
          <div className="flex-1 min-w-0 flex flex-col gap-4 min-h-0">
            {/* Graph panel — populated by the selected candidate */}
            <div className="flex-[2] min-h-0 flex flex-col overflow-hidden rounded-2xl border border-[#e8e8e8] shadow-sm bg-white">
              {selectedGraph && selectedDay ? (
                <>
                  <div className="shrink-0 flex items-center justify-between gap-2 px-4 py-3 border-b border-[#e8e8e8] bg-[#fafafa]">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md ${selectedDay.bg} ${selectedDay.text}`}
                      >
                        {selectedDay.short}
                      </span>
                      <span className="font-bold text-[#333] tabular-nums text-sm">
                        {formatTime(graphStartTime(selectedGraph))}
                      </span>
                      <span className="font-semibold text-[#222] text-sm truncate">
                        {selectedGraph.subject.name}
                      </span>
                      <span className="text-[11px] text-[#aaa] shrink-0">
                        {selectedGraph.nodes.length} aulas
                      </span>
                    </div>
                    {selectedValid ? (
                      <button
                        onClick={() => {
                          const id = handleCreateGroup(selectedGraph.candidate_group_id);
                          if (id) requestAnimationFrame(() => revealGroup(id));
                        }}
                        className="shrink-0 bg-[#1e2028] text-white font-semibold px-3 py-1.5 rounded-lg text-[11px] hover:bg-[#2a2d37] transition-colors whitespace-nowrap cursor-pointer"
                      >
                        Criar grupo ({selectedSelection.size})
                      </button>
                    ) : selectedSelection.size > 0 ? (
                      <span className="shrink-0 text-[11px] text-[#bbb] font-medium whitespace-nowrap">
                        Liga ≥2 turmas adjacentes
                      </span>
                    ) : selectedAllAssigned ? (
                      <span className="shrink-0 text-[11px] text-emerald-600 font-semibold whitespace-nowrap">
                        Todas agrupadas
                      </span>
                    ) : selectedCanGroupAll ? (
                      <button
                        onClick={() => {
                          const id = handleGroupAll(selectedGraph.candidate_group_id);
                          if (id) requestAnimationFrame(() => revealGroup(id));
                        }}
                        className="shrink-0 bg-[#1e2028] text-white font-semibold px-3 py-1.5 rounded-lg text-[11px] hover:bg-[#2a2d37] transition-colors whitespace-nowrap cursor-pointer"
                      >
                        Agrupar todas ({selectedUnassignedCount})
                      </button>
                    ) : (
                      <span className="shrink-0 text-[11px] text-[#bbb] font-medium whitespace-nowrap">
                        Clica em turmas ligadas
                      </span>
                    )}
                  </div>
                  <div className="flex-1 min-h-0 overflow-hidden p-4">
                    <ParallelGraph
                      key={selectedGraph.candidate_group_id}
                      graph={selectedGraph}
                      selected={selectedSelection}
                      assigned={assignedBlockIds}
                      onToggleNode={(blockId) =>
                        handleToggleNode(selectedGraph.candidate_group_id, blockId)
                      }
                      onTapAssigned={handleRevealGroup}
                      sessionTypeStyle={sessionTypeStyle}
                    />
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center p-8">
                  <p className="text-sm text-[#aaa] text-center">
                    {loadingCandidates
                      ? "A carregar candidatos…"
                      : "Seleciona um candidato à esquerda para ver o grafo."}
                  </p>
                </div>
              )}
            </div>

            {/* Selected groups panel */}
            <div className="flex-[2] min-h-0 flex flex-col">
              <h2 className="font-bold text-[#333] text-base mb-3 shrink-0">Selecionadas</h2>
              <div
                ref={groupsPanelRef}
                className="flex-1 overflow-y-auto pb-2 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60"
              >
                {loadingCandidates ? (
                  <CandidatesLoadingSkeleton />
                ) : groupViewsBySubject.size === 0 ? (
                  <p className="text-xs text-[#aaa] text-center py-8">Nenhum grupo criado ainda.</p>
                ) : (
                  <div
                    ref={groupsScrollRef}
                    className="flex gap-4 overflow-x-auto [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60"
                  >
                    {[...groupViewsBySubject.entries()]
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([subjName, items]) => {
                        const isActive = subjName === activeSubject;
                        return (
                          <div
                            key={subjName}
                            ref={isActive ? activeGroupColRef : undefined}
                            className={`parallel-col-enter flex flex-col gap-1.5 transition-[flex-grow,min-width] duration-300 ease-out ${
                              isActive ? "flex-[2.75] min-w-[340px]" : "flex-1 min-w-[210px]"
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <p className="text-[11px] font-bold tracking-widest uppercase text-[#888]">
                                {subjName}
                              </p>
                              <span className="text-[10px] font-semibold text-[#bbb] tabular-nums">
                                {items.length}
                              </span>
                              <div className="flex-1 h-px bg-[#e0e0e0]" />
                            </div>
                            <div className="flex flex-col gap-1.5">
                              {items.map(({ group, weekday, startTime, blocks }) => {
                                const day = dayConfig(weekday);
                                const saved = savedGroupIds.has(group.id);
                                const highlighted = highlightedGroupId === group.id;
                                return (
                                  <div
                                    key={group.id}
                                    ref={(el) => {
                                      if (el) groupCardRefs.current.set(group.id, el);
                                      else groupCardRefs.current.delete(group.id);
                                    }}
                                    className={`flex items-stretch overflow-hidden rounded-lg border bg-white ${
                                      saved ? "border-[#e4e4e4]" : "border-emerald-300"
                                    } ${highlighted ? "parallel-group-pulse" : ""}`}
                                  >
                                    <div
                                      className={`w-1 shrink-0 ${saved ? "bg-[#c8c8c8]" : "bg-emerald-400"}`}
                                    />
                                    <div className="flex-1 min-w-0 px-2.5 py-2">
                                      <div className="flex items-center gap-2 mb-1.5">
                                        <span
                                          className={`text-[10px] font-bold tracking-wider px-1.5 py-0.5 rounded ${day.bg} ${day.text}`}
                                        >
                                          {day.short}
                                        </span>
                                        <span className="text-[12px] font-bold tabular-nums text-[#333]">
                                          {formatTime(startTime)}
                                        </span>
                                        <span
                                          className={`text-[10px] font-semibold ${saved ? "text-[#aaa]" : "text-emerald-600"}`}
                                        >
                                          {saved ? "Guardada" : "Nova"}
                                        </span>
                                        <button
                                          onClick={() => handleRemoveGroup(group.id)}
                                          className="ml-auto flex items-center justify-center w-5 h-5 rounded text-[#bbb] hover:bg-red-50 hover:text-red-600 transition-colors text-sm leading-none cursor-pointer"
                                          title="Remover grupo"
                                        >
                                          ×
                                        </button>
                                      </div>
                                      <div className="flex flex-col gap-1">
                                        {blocks.map((block) => {
                                          const typeStyle = sessionTypeStyle(block.type);
                                          return (
                                            <div
                                              key={block.blockId}
                                              className="flex items-center gap-1.5"
                                            >
                                              <span
                                                className={`shrink-0 w-7 text-center text-[10px] font-bold px-1 py-0.5 rounded ${typeStyle.bg} ${typeStyle.text}`}
                                              >
                                                {block.type}
                                              </span>
                                              <div className="flex flex-wrap gap-1">
                                                {block.codes.map((code) => (
                                                  <span
                                                    key={`${block.blockId}-${code}`}
                                                    className="rounded px-1.5 py-0.5 text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200"
                                                  >
                                                    {code}
                                                  </span>
                                                ))}
                                              </div>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-bold text-[#222] text-base mb-1">Tens a certeza?</h3>
            <p className="text-sm text-[#666] mb-6">
              Todas as seleções guardadas serão apagadas. Esta ação não pode ser desfeita.
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={confirmReset}
                className="bg-red-600 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-red-500 transition-colors cursor-pointer"
              >
                Recomeçar
              </button>
              <button
                onClick={() => setShowResetModal(false)}
                className="text-[#666] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition-colors cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {showUnsavedModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-bold text-[#222] text-base mb-1">Tens mudanças por guardar</h3>
            <p className="text-sm text-[#666] mb-6">
              Se saíres sem guardar, as alterações feitas serão perdidas.
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => void handleSaveAndExit()}
                disabled={saving}
                className="bg-[#8c2d19] text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-[#a33520] transition-colors disabled:opacity-50 cursor-pointer"
              >
                {saving ? "A guardar..." : "Guardar e sair"}
              </button>
              <button
                onClick={handleExitWithoutSaving}
                disabled={saving}
                className="border border-red-400 text-red-500 font-semibold px-4 py-2 rounded-lg text-sm hover:bg-red-50 transition-colors disabled:opacity-50 cursor-pointer"
              >
                Sair sem guardar
              </button>
              <button
                onClick={() => setShowUnsavedModal(false)}
                disabled={saving}
                className="text-[#666] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition-colors disabled:opacity-50 cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
