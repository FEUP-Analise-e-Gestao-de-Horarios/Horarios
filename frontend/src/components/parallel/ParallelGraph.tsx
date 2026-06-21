import { useMemo } from "react";
import type { ParallelBlockNode, ParallelCandidateGraph, UUID } from "@/types/parallelSessions";
import { layoutNodes } from "./parallelGraph";

interface ParallelGraphProps {
  graph: ParallelCandidateGraph;
  /** Blocks the user has currently selected to form a new group. */
  selected: Set<UUID>;
  /** Blocks already assigned to a (draft or confirmed) group — locked. */
  assigned: Set<UUID>;
  onToggleNode: (blockId: UUID) => void;
  sessionTypeStyle: (type: string) => { bg: string; text: string };
}

const NODE_PAD = 96;

export default function ParallelGraph({
  graph,
  selected,
  assigned,
  onToggleNode,
  sessionTypeStyle,
}: ParallelGraphProps) {
  const ids = useMemo(() => graph.nodes.map((n) => n.original_block_id), [graph.nodes]);
  const nodeById = useMemo(() => {
    const map = new Map<UUID, ParallelBlockNode>();
    for (const node of graph.nodes) map.set(node.original_block_id, node);
    return map;
  }, [graph.nodes]);

  const radius = ids.length <= 2 ? 96 : Math.max(96, ids.length * 22);
  const side = 2 * radius + NODE_PAD * 2;
  const center = side / 2;

  const positions = useMemo(() => layoutNodes(ids, radius), [ids, radius]);

  return (
    <div className="relative mx-auto" style={{ width: side, height: side }}>
      <svg className="absolute inset-0 pointer-events-none" width={side} height={side} aria-hidden>
        {graph.edges.map(([a, b], i) => {
          const pa = positions.get(a);
          const pb = positions.get(b);
          if (!pa || !pb) return null;
          const bothSelected = selected.has(a) && selected.has(b);
          return (
            <line
              key={`${a}-${b}-${i}`}
              x1={center + pa.x}
              y1={center + pa.y}
              x2={center + pb.x}
              y2={center + pb.y}
              stroke={bothSelected ? "#f59e0b" : "#d1d5db"}
              strokeWidth={bothSelected ? 2.5 : 1.5}
            />
          );
        })}
      </svg>

      {ids.map((id) => {
        const node = nodeById.get(id);
        const pos = positions.get(id);
        if (!node || !pos) return null;
        const isAssigned = assigned.has(id);
        const isSelected = selected.has(id);
        const typeStyle = sessionTypeStyle(node.session.type);
        const codes = node.classes.map((c) => c.code).join(" ");
        return (
          <button
            key={id}
            type="button"
            disabled={isAssigned}
            onClick={() => onToggleNode(id)}
            title={isAssigned ? "Já pertence a um grupo" : codes}
            style={{
              left: center + pos.x,
              top: center + pos.y,
              transform: "translate(-50%, -50%)",
            }}
            className={`absolute flex max-w-[150px] flex-col items-center gap-1 rounded-xl border px-2.5 py-1.5 shadow-sm transition-colors ${
              isAssigned
                ? "cursor-default border-dashed border-gray-300 bg-gray-100 opacity-60"
                : isSelected
                  ? "cursor-pointer border-amber-400 bg-amber-50 ring-2 ring-amber-300"
                  : "cursor-pointer border-gray-300 bg-white hover:border-gray-400 hover:bg-[#fffdf5]"
            }`}
          >
            <span
              className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold ${typeStyle.bg} ${typeStyle.text}`}
            >
              {node.session.type}
            </span>
            <span className="max-w-full truncate text-[11px] font-bold tabular-nums text-[#333]">
              {codes}
            </span>
            {isAssigned && (
              <span className="text-[9px] font-semibold uppercase tracking-wide text-gray-400">
                em grupo
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
