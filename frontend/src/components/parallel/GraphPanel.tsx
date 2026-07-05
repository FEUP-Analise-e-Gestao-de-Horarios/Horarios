import type { ParallelCandidateGraph, UUID } from "@/types/parallelSessions";
import ParallelGraph from "./ParallelGraph";
import { dayConfig, formatTime, graphStartTime, sessionTypeStyle } from "./parallelDisplay";

/**
 * The graph panel (top of the right column): a header describing the selected
 * candidate plus the contextual grouping action, and the interactive
 * {@link ParallelGraph} beneath it. Renders an empty prompt when no candidate is
 * open.
 */
export default function GraphPanel({
  selectedGraph,
  selectedSelection,
  selectedValid,
  selectedAllAssigned,
  selectedCanGroupAll,
  selectedUnassignedCount,
  assignedBlockIds,
  loadingCandidates,
  onCreateGroup,
  onGroupAll,
  onToggleNode,
  onTapAssigned,
}: {
  selectedGraph: ParallelCandidateGraph | null;
  selectedSelection: Set<UUID>;
  selectedValid: boolean;
  selectedAllAssigned: boolean;
  selectedCanGroupAll: boolean;
  selectedUnassignedCount: number;
  assignedBlockIds: Set<UUID>;
  loadingCandidates: boolean;
  onCreateGroup: () => void;
  onGroupAll: () => void;
  onToggleNode: (blockId: UUID) => void;
  onTapAssigned: (blockId: UUID) => void;
}) {
  const selectedDay = selectedGraph ? dayConfig(selectedGraph.weekday) : null;

  return (
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
                onClick={onCreateGroup}
                className="shrink-0 bg-[#1e2028] text-white font-semibold px-3 py-1.5 rounded-lg text-[11px] hover:bg-[#2a2d37] transition-colors whitespace-nowrap cursor-pointer"
              >
                Criar grupo ({selectedSelection.size})
              </button>
            ) : selectedSelection.size > 0 ? (
              <span className="shrink-0 py-1.5 text-[11px] text-[#bbb] font-medium whitespace-nowrap">
                Liga ≥2 turmas adjacentes
              </span>
            ) : selectedAllAssigned ? (
              <span className="shrink-0 py-1.5 text-[11px] text-emerald-600 font-semibold whitespace-nowrap">
                Todas agrupadas
              </span>
            ) : selectedCanGroupAll ? (
              <button
                onClick={onGroupAll}
                className="shrink-0 bg-[#1e2028] text-white font-semibold px-3 py-1.5 rounded-lg text-[11px] hover:bg-[#2a2d37] transition-colors whitespace-nowrap cursor-pointer"
              >
                Agrupar todas ({selectedUnassignedCount})
              </button>
            ) : (
              <span className="shrink-0 py-1.5 text-[11px] text-[#bbb] font-medium whitespace-nowrap">
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
              onToggleNode={onToggleNode}
              onTapAssigned={onTapAssigned}
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
  );
}
