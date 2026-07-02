import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight } from "lucide-react";
import { useParallelSessions } from "@/api/hooks/useParallelSessions";
import { DAY_ORDER, type ParallelCandidateGraph } from "@/types/parallelSessions";
import DegreeDropdown from "@/components/schedule/DegreeDropdown";
import MultiDropdown from "@/components/schedule/MultiDropdown";
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
  const [openDropdown, setOpenDropdown] = useState<"degree" | "year" | null>(null);
  // The candidate whose graph is shown in the top-right panel.
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const headerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (headerRef.current && !headerRef.current.contains(e.target as Node)) {
        setOpenDropdown(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

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
    groupViewsBySubject,
    savedGroupIds,
    saving,
    saveStatus,
    showUnsavedModal,
    setShowUnsavedModal,
    showResetModal,
    setShowResetModal,
    handleDegreeClick,
    handleYearToggle,
    handleToggleNode,
    handleCreateGroup,
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

  const yearOptions = useMemo(
    () => yearsWithCandidates.map((y) => ({ value: y.id, label: `${y.number}º Ano` })),
    [yearsWithCandidates],
  );

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

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <header
        ref={headerRef}
        className="shrink-0 sticky top-0 z-50 px-6 py-3 bg-[#1e2028] flex items-center gap-2 w-full flex-wrap border-b border-gray-700"
      >
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

        <div className="w-px h-6 bg-gray-600 mx-1" />

        {degreesError ? (
          <span className="text-xs text-red-400">{degreesError}</span>
        ) : (
          <DegreeDropdown
            degrees={degrees}
            selected={selectedDegree}
            onSelect={(degree) => {
              handleDegreeClick(degree);
              setOpenDropdown(null);
            }}
            open={openDropdown === "degree"}
            onToggle={() => setOpenDropdown((prev) => (prev === "degree" ? null : "degree"))}
            loading={loadingDegrees}
          />
        )}

        {yearsError ? (
          <span className="text-xs text-red-400">{yearsError}</span>
        ) : (
          <MultiDropdown
            label="Ano"
            options={yearOptions}
            selected={yearOptions.filter((o) => selectedYearIds.has(o.value)).map((o) => o.value)}
            onSelect={(newValues) => {
              const next = new Set(newValues);
              for (const o of yearOptions) {
                if (selectedYearIds.has(o.value) !== next.has(o.value)) handleYearToggle(o.value);
              }
            }}
            open={openDropdown === "year"}
            onToggle={() => setOpenDropdown((prev) => (prev === "year" ? null : "year"))}
            disabled={!selectedDegree || loadingYears}
            showLabel
          />
        )}

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
        {!selectedDegree ? (
          <p className="text-sm text-[#aaa] text-center mt-16">
            Seleciona um curso para ver as aulas em paralelo.
          </p>
        ) : (
          <div className="h-full max-w-7xl mx-auto px-6 py-6 flex gap-6">
            {/* Left column: list of candidates */}
            <div className="w-[360px] shrink-0 flex flex-col min-h-0">
              <div className="flex items-center justify-between mb-3 shrink-0">
                <h2 className="font-bold text-[#333] text-base">Candidatos a paralelas</h2>
              </div>
              <div className="flex-1 overflow-y-auto pb-6 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                {loadingCandidates ? (
                  <CandidatesLoadingSkeleton />
                ) : candidatesError ? (
                  <p className="text-sm text-red-600">{candidatesError}</p>
                ) : graphsBySubject.size === 0 ? (
                  <p className="text-sm text-[#aaa]">Sem aulas em paralelo.</p>
                ) : (
                  <div className="flex flex-col gap-4">
                    {[...graphsBySubject.entries()]
                      .sort(([a], [b]) => a.localeCompare(b))
                      .map(([subjectName, subjectGraphs]) => (
                        <div
                          key={subjectName}
                          className="overflow-hidden rounded-2xl border border-[#e8e8e8] shadow-sm bg-white"
                        >
                          <div className="px-4 py-2.5 bg-[#fafafa] border-b border-[#e8e8e8]">
                            <p className="font-semibold text-[#222] text-sm">{subjectName}</p>
                          </div>
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
                                    setSelectedCandidateId(
                                      isSelected ? null : graph.candidate_group_id,
                                    )
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
                                  <span className="text-[11px] text-[#aaa]">
                                    {graph.nodes.length} turmas
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
                                    <ChevronRight
                                      className={`w-4 h-4 shrink-0 transition-colors ${isSelected ? "text-[#8c2d19]" : "text-[#ccc]"}`}
                                    />
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right column: graph (top) + selected groups (bottom) */}
            <div className="flex-1 min-w-0 flex flex-col gap-4 min-h-0">
              {/* Graph panel — populated by the selected candidate */}
              <div className="flex-[3] min-h-0 flex flex-col overflow-hidden rounded-2xl border border-[#e8e8e8] shadow-sm bg-white">
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
                          {selectedGraph.nodes.length} turmas
                        </span>
                      </div>
                      {selectedValid ? (
                        <button
                          onClick={() => handleCreateGroup(selectedGraph.candidate_group_id)}
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
                <div className="flex-1 overflow-y-auto pb-2 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                  {loadingCandidates ? (
                    <CandidatesLoadingSkeleton />
                  ) : groupViewsBySubject.size === 0 ? (
                    <p className="text-xs text-[#aaa] text-center py-8">
                      Nenhum grupo criado ainda.
                    </p>
                  ) : (
                    <div className="flex flex-col gap-5">
                      {[...groupViewsBySubject.entries()]
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([subjName, items]) => (
                          <div
                            key={subjName}
                            className="overflow-hidden rounded-2xl border border-[#d4d4d4] shadow-sm"
                          >
                            <div className="px-3 py-2 bg-[#e8e8e8] border-b border-[#d4d4d4]">
                              <p className="text-[11px] font-bold tracking-widest uppercase text-[#444]">
                                {subjName}
                              </p>
                            </div>
                            <div className="flex flex-col gap-2 p-2">
                              {items.map(({ group, weekday, startTime, blocks }) => {
                                const day = dayConfig(weekday);
                                const saved = savedGroupIds.has(group.id);
                                return (
                                  <div
                                    key={group.id}
                                    className="overflow-hidden rounded-xl shadow-sm bg-white border border-[#e8e8e8]"
                                  >
                                    <div
                                      className={`px-3 py-1.5 flex items-center justify-between ${saved ? "bg-[#1e2028]" : "bg-emerald-200"}`}
                                    >
                                      <div className="flex items-center gap-2">
                                        <span
                                          className={`text-[10px] font-bold tracking-wider px-1.5 py-0.5 rounded ${day.bg} ${day.text}`}
                                        >
                                          {day.short}
                                        </span>
                                        <span
                                          className={`text-[11px] font-bold tabular-nums ${saved ? "text-gray-300" : "text-emerald-900"}`}
                                        >
                                          {formatTime(startTime)}
                                        </span>
                                      </div>
                                      <button
                                        onClick={() => handleRemoveGroup(group.id)}
                                        className="flex items-center justify-center w-5 h-5 rounded bg-red-600 hover:bg-red-500 transition-colors text-white text-xs font-bold leading-none cursor-pointer"
                                        title="Remover grupo"
                                      >
                                        ×
                                      </button>
                                    </div>
                                    <div className="px-3 py-2 flex flex-col gap-1">
                                      {blocks.map((block) => {
                                        const typeStyle = sessionTypeStyle(block.type);
                                        return (
                                          <div
                                            key={block.blockId}
                                            className="flex items-center gap-1"
                                          >
                                            <span
                                              className={`shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded ${typeStyle.bg} ${typeStyle.text}`}
                                            >
                                              {block.type}
                                            </span>
                                            <div className="flex flex-wrap gap-1">
                                              {block.codes.map((code) => (
                                                <span
                                                  key={`${block.blockId}-${code}`}
                                                  className="rounded px-1.5 py-0.5 text-[11px] font-semibold bg-[#ffc107] text-[#222]"
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
                                );
                              })}
                            </div>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
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
