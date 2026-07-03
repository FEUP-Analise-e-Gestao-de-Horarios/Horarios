import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight } from "lucide-react";
import { type GroupView, useParallelSessions } from "@/api/hooks/useParallelSessions";
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

/**
 * A single group card in the "Selecionadas" panel, animated by its lifecycle:
 * a freshly-created card expands in shifted right with a green rail and only
 * slides back once the server confirms; a card being deleted turns its rail red
 * and shifts right, then — once confirmed — collapses out so the others slide
 * up into its place. The outer grid drives the height collapse (enter/leave)
 * and the rightward shift; the middle wrapper carries the reveal pulse.
 */
function GroupCard({
  view,
  highlighted,
  onRemove,
  registerRef,
}: {
  view: GroupView;
  highlighted: boolean;
  onRemove: () => void;
  registerRef: (el: HTMLDivElement | null) => void;
}) {
  const { group, weekday, startTime, blocks } = view;
  const status = group.status;
  const day = dayConfig(weekday);

  // A freshly-created card appears in its normal place, then slides right on the
  // next frame and holds there while its create confirms. `moved` gates that
  // delay so the shift animates from rest instead of starting shifted. Two RAFs
  // ensure the browser paints the un-shifted frame before the flip.
  const [moved, setMoved] = useState(status !== "creating");
  useEffect(() => {
    if (moved) return;
    let inner = 0;
    const outer = requestAnimationFrame(() => {
      inner = requestAnimationFrame(() => setMoved(true));
    });
    return () => {
      cancelAnimationFrame(outer);
      cancelAnimationFrame(inner);
    };
  }, [moved]);

  // Pending cards (create confirming or delete confirming) hold shifted to the
  // right; a settled "saved" card — and a confirmed-deleted card releasing on
  // its way out — sit flush.
  const shifted = status === "deleting" || (status === "creating" && moved);
  // A confirmed-deleted card releases the shift, fades, and collapses its row so
  // the others slide up into its place.
  const open = status !== "leaving";
  const leaving = status === "leaving";

  const borderColor =
    status === "deleting"
      ? "border-red-400"
      : status === "creating"
        ? "border-emerald-300"
        : "border-[#e4e4e4]";
  const railColor =
    status === "deleting"
      ? "bg-red-400"
      : status === "creating"
        ? "bg-emerald-400"
        : "bg-[#c8c8c8]";
  // One-shot glow that plays when the card enters its pending state.
  const glow = highlighted
    ? "parallel-group-pulse"
    : status === "creating"
      ? "parallel-group-added"
      : status === "deleting"
        ? "parallel-group-removing"
        : "";

  return (
    <div
      ref={registerRef}
      className={`grid transition-all ease-out ${leaving ? "duration-500" : "duration-300"} ${
        open ? "grid-rows-[1fr] opacity-100 mb-1.5" : "grid-rows-[0fr] opacity-0 mb-0"
      } ${shifted ? "translate-x-4" : "translate-x-0"}`}
    >
      <div className={`min-h-0 overflow-hidden rounded-lg ${glow}`}>
        <div
          className={`flex items-stretch overflow-hidden rounded-lg border bg-white transition-colors duration-300 ${borderColor}`}
        >
          <div className={`w-1 shrink-0 transition-colors duration-300 ${railColor}`} />
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
              <button
                onClick={onRemove}
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
                  <div key={block.blockId} className="group/codes flex items-center gap-1.5">
                    <span
                      className={`shrink-0 w-7 text-center text-[10px] font-bold px-1 py-0.5 rounded ${typeStyle.bg} ${typeStyle.text}`}
                    >
                      {block.type}
                    </span>
                    {/* Codes collapse to one line with a right-edge fade;
                        hovering the row wraps them to reveal the full list. */}
                    <div className="flex min-w-0 flex-1 flex-nowrap gap-1 overflow-hidden [mask-image:linear-gradient(to_right,black_calc(100%_-_20px),transparent)] [-webkit-mask-image:linear-gradient(to_right,black_calc(100%_-_20px),transparent)] group-hover/codes:flex-wrap group-hover/codes:overflow-visible group-hover/codes:[mask-image:none] group-hover/codes:[-webkit-mask-image:none]">
                      {block.codes.map((code) => (
                        <span
                          key={`${block.blockId}-${code}`}
                          className="shrink-0 whitespace-nowrap rounded px-1.5 py-0.5 text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200"
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
      </div>
    </div>
  );
}

export default function ParallelClassesPage() {
  // Per-subject memory of which candidate's graph is open, mirroring how the
  // year is remembered per degree and the subject per year. Keeps a graph
  // selected only while its subject is active, and restores it on return.
  const [selectedCandidateBySubject, setSelectedCandidateBySubject] = useState<
    Record<string, string | null>
  >({});
  // Per-year memory of the chosen subject.
  const [selectedSubjectByYear, setSelectedSubjectByYear] = useState<Record<string, string>>({});

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
    saving,
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

  // The single selected year driving the candidate list.
  const activeYearId = yearsWithCandidates.find((y) => selectedYearIds.has(y.id))?.id ?? null;

  // Resolve the effective subject: the one remembered for the active year when it
  // still exists, else the first available (e.g. after a degree/year change).
  const rememberedSubject = activeYearId ? selectedSubjectByYear[activeYearId] : undefined;
  const activeSubject =
    rememberedSubject && subjectNames.includes(rememberedSubject)
      ? rememberedSubject
      : (subjectNames[0] ?? null);

  const subjectGraphs = activeSubject ? (graphsBySubject.get(activeSubject) ?? []) : [];

  // The open candidate, remembered per subject and constrained to it so a graph
  // only stays selected while its subject is active.
  const selectedCandidateId = activeSubject
    ? (selectedCandidateBySubject[activeSubject] ?? null)
    : null;

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

  // Scroll a group card into view without the pulse — used on create, where the
  // card's own enter/shift animation is the feedback (and a pulse would fight
  // its rightward shift transform).
  const scrollGroupIntoView = useCallback((groupId: string) => {
    groupCardRefs.current
      .get(groupId)
      ?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
  }, []);

  // Tap on an already-grouped node reveals the group it belongs to.
  const handleRevealGroup = useCallback(
    (blockId: string) => {
      const groupId = groupIdByBlock.get(blockId);
      if (groupId) revealGroup(groupId);
    },
    [groupIdByBlock, revealGroup],
  );

  // Remember the chosen subject for the active year.
  const handleSelectSubject = (name: string) => {
    if (activeYearId) setSelectedSubjectByYear((prev) => ({ ...prev, [activeYearId]: name }));
  };

  // Open/close a candidate's graph, remembered per subject. Opening one that
  // already has exactly one group also jumps to that group.
  const handleSelectCandidate = (candidateId: string) => {
    if (!activeSubject) return;
    const closing = selectedCandidateBySubject[activeSubject] === candidateId;
    setSelectedCandidateBySubject((prev) => ({
      ...prev,
      [activeSubject]: closing ? null : candidateId,
    }));
    if (!closing) {
      const ids = groupIdsByCandidate.get(candidateId);
      if (ids && ids.length === 1) requestAnimationFrame(() => revealGroup(ids[0]!));
    }
  };

  // The candidate currently driving the graph panel, resolved within the active
  // subject so it collapses when its subject (or year) is no longer selected.
  const selectedGraph =
    (selectedCandidateId &&
      subjectGraphs.find((g) => g.candidate_group_id === selectedCandidateId)) ||
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
          <button
            onClick={handleReset}
            disabled={saving}
            className="bg-transparent text-red-400 font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            Recomeçar
          </button>
          <button
            type="button"
            disabled={saving}
            aria-busy={saving}
            className="bg-emerald-600 text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap text-center min-w-[110px] hover:bg-emerald-500 transition-colors disabled:opacity-70 disabled:cursor-not-allowed cursor-pointer"
          >
            {saving ? (
              <span className="flex h-5 items-center justify-center gap-1" aria-label="A guardar">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-bounce" />
              </span>
            ) : (
              "Terminar"
            )}
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
                              onClick={() => handleSelectSubject(name)}
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
                          onClick={() => handleSelectCandidate(graph.candidate_group_id)}
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
            <div className="flex-[38] min-h-0 flex flex-col overflow-hidden rounded-2xl border border-[#e8e8e8] shadow-sm bg-white">
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
                          if (id) requestAnimationFrame(() => scrollGroupIntoView(id));
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
                          if (id) requestAnimationFrame(() => scrollGroupIntoView(id));
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
            <div className="flex-[42] min-h-0 flex flex-col">
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
                            <div className="flex flex-col">
                              {items.map((view) => (
                                <GroupCard
                                  key={view.group.id}
                                  view={view}
                                  highlighted={highlightedGroupId === view.group.id}
                                  onRemove={() => handleRemoveGroup(view.group.id)}
                                  registerRef={(el) => {
                                    if (el) groupCardRefs.current.set(view.group.id, el);
                                    else groupCardRefs.current.delete(view.group.id);
                                  }}
                                />
                              ))}
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
    </div>
  );
}
