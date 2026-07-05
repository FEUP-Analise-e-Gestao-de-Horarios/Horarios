import { ChevronRight } from "lucide-react";
import type { GroupView } from "@/api/hooks/parallel/sessions";
import type { ParallelCandidateGraph, UUID } from "@/types/parallelSessions";
import CandidatesLoadingSkeleton from "./CandidatesLoadingSkeleton";
import { dayConfig, EMPTY_SELECTION, formatTime, graphStartTime } from "./parallelDisplay";

/**
 * The scrollable candidate area of the left column: the active subject's header
 * (with Repor / Confirmar actions) followed by one row per candidate graph, each
 * showing its day, start time, in-progress selection count, formed-group count
 * and total classes.
 */
export default function CandidateList({
  loadingCandidates,
  candidatesError,
  hasSubjects,
  hasSelectedDegree,
  activeSubject,
  activeSubjectGroupViews,
  activeSubjectConfirmed,
  saving,
  onResetActiveSubject,
  onUnconfirmActiveSubject,
  onConfirmActiveSubject,
  subjectGraphs,
  selectionByGroup,
  assignedBlockIds,
  groupIdsByCandidate,
  selectedCandidateId,
  onSelectCandidate,
}: {
  loadingCandidates: boolean;
  candidatesError: string | null;
  hasSubjects: boolean;
  hasSelectedDegree: boolean;
  activeSubject: string | null;
  activeSubjectGroupViews: GroupView[];
  activeSubjectConfirmed: boolean;
  saving: boolean;
  onResetActiveSubject: () => void;
  onUnconfirmActiveSubject: () => void;
  onConfirmActiveSubject: () => void;
  subjectGraphs: ParallelCandidateGraph[];
  selectionByGroup: Record<UUID, Set<UUID>>;
  assignedBlockIds: Set<UUID>;
  groupIdsByCandidate: Map<string, string[]>;
  selectedCandidateId: string | null;
  onSelectCandidate: (candidateId: string) => void;
}) {
  return (
    <div className="flex-1 overflow-y-auto pb-6 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
      {loadingCandidates ? (
        <CandidatesLoadingSkeleton />
      ) : candidatesError ? (
        <p className="text-sm text-red-600">{candidatesError}</p>
      ) : !hasSubjects ? (
        <p className="text-sm text-[#aaa]">
          {hasSelectedDegree ? "Sem aulas em paralelo." : "Seleciona um curso para começar."}
        </p>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-[#e8e8e8] shadow-sm bg-white">
          {activeSubject && (
            <div className="flex items-center justify-between gap-2 px-4 py-2.5 bg-[#fafafa] border-b border-[#e8e8e8]">
              <p className="font-semibold text-[#222] text-sm truncate">{activeSubject}</p>
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  type="button"
                  onClick={onResetActiveSubject}
                  disabled={activeSubjectGroupViews.length === 0 || saving}
                  title="Apagar os grupos desta cadeira"
                  className="rounded-md border border-[#e0e0e0] bg-white px-2.5 py-1 text-[11px] font-semibold text-[#777] transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-600 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer disabled:hover:border-[#e0e0e0] disabled:hover:bg-white disabled:hover:text-[#777]"
                >
                  Repor
                </button>
                {activeSubjectConfirmed ? (
                  <button
                    type="button"
                    onClick={onUnconfirmActiveSubject}
                    disabled={saving}
                    title="Clica para reabrir esta cadeira"
                    className="group/confirm rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors cursor-pointer bg-emerald-100 text-emerald-700 hover:bg-red-100 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <span className="group-hover/confirm:hidden">Confirmada</span>
                    <span className="hidden group-hover/confirm:inline">Desmarcar</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={onConfirmActiveSubject}
                    disabled={saving}
                    className="rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors cursor-pointer bg-emerald-600 text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Confirmar
                  </button>
                )}
              </div>
            </div>
          )}
          <div className="flex flex-col divide-y divide-[#f0f0f0]">
            {subjectGraphs.map((graph) => {
              const day = dayConfig(graph.weekday);
              const selection = selectionByGroup[graph.candidate_group_id] ?? EMPTY_SELECTION;
              const allAssigned = graph.nodes.every((n) =>
                assignedBlockIds.has(n.original_block_id),
              );
              const groupCount = groupIdsByCandidate.get(graph.candidate_group_id)?.length ?? 0;
              const isSelected = selectedCandidateId === graph.candidate_group_id;
              return (
                <button
                  key={graph.candidate_group_id}
                  type="button"
                  onClick={() => onSelectCandidate(graph.candidate_group_id)}
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
                    {groupCount > 0 && (
                      <span
                        className={`text-[11px] font-semibold ${
                          allAssigned ? "text-emerald-600" : "text-violet-600"
                        }`}
                      >
                        {groupCount} {groupCount === 1 ? "grupo" : "grupos"}
                      </span>
                    )}
                    <span className="text-[11px] text-[#aaa]">{graph.nodes.length} aulas</span>
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
  );
}
