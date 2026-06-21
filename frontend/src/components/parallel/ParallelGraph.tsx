import { useEffect, useMemo, useState } from "react";
import type { ParallelBlockNode, ParallelCandidateGraph, UUID } from "@/types/parallelSessions";
import { forceLayout } from "./parallelGraph";

interface ParallelGraphProps {
  graph: ParallelCandidateGraph;
  /** Blocks the user has currently selected to form a new group. */
  selected: Set<UUID>;
  /** Blocks already assigned to a (draft or confirmed) group — locked. */
  assigned: Set<UUID>;
  onToggleNode: (blockId: UUID) => void;
  sessionTypeStyle: (type: string) => { bg: string; text: string };
}

const NODE_PAD = 84;
/** Per-node delay of the entrance burst, in ms. */
const STAGGER = 45;

/** Format an ISO date (YYYY-MM-DD) as DD/MM. */
function formatWeek(dateStr: string): string {
  const parts = dateStr.split("-");
  return parts.length === 3 ? `${parts[2]}/${parts[1]}` : dateStr;
}

/** A block's active week span, e.g. "15/09" or "15/09–20/12". */
function weekRange(first: string, last: string): string {
  const a = formatWeek(first);
  const b = formatWeek(last);
  return a === b ? a : `${a}–${b}`;
}

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
  const orderIndex = useMemo(() => {
    const map = new Map<UUID, number>();
    ids.forEach((id, i) => map.set(id, i));
    return map;
  }, [ids]);

  const positions = useMemo(
    () => forceLayout(ids, graph.edges, { linkDistance: 120 }),
    [ids, graph.edges],
  );

  // Container bounds derived from the laid-out positions.
  const { width, height, place } = useMemo(() => {
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const p of positions.values()) {
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    }
    if (!Number.isFinite(minX)) {
      minX = minY = maxX = maxY = 0;
    }
    const w = maxX - minX + NODE_PAD * 2;
    const h = maxY - minY + NODE_PAD * 2;
    const place = (p: { x: number; y: number }) => ({
      left: p.x - minX + NODE_PAD,
      top: p.y - minY + NODE_PAD,
    });
    return { width: w, height: h, place };
  }, [positions]);

  // Entrance burst: nodes pop in sequence once the graph mounts.
  const [appear, setAppear] = useState(false);
  useEffect(() => {
    const raf = requestAnimationFrame(() => setAppear(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="relative mx-auto" style={{ width, height }}>
      <svg
        className="absolute inset-0 pointer-events-none"
        width={width}
        height={height}
        aria-hidden
      >
        {graph.edges.map(([a, b], i) => {
          const pa = positions.get(a);
          const pb = positions.get(b);
          if (!pa || !pb) return null;
          const la = place(pa);
          const lb = place(pb);
          const bothSelected = selected.has(a) && selected.has(b);
          const delay = (Math.max(orderIndex.get(a) ?? 0, orderIndex.get(b) ?? 0) + 1) * STAGGER;
          return (
            <line
              key={`${a}-${b}-${i}`}
              x1={la.left}
              y1={la.top}
              x2={lb.left}
              y2={lb.top}
              stroke={bothSelected ? "#f59e0b" : "#d1d5db"}
              strokeWidth={bothSelected ? 2.5 : 1.5}
              style={{
                opacity: appear ? 1 : 0,
                transition: "opacity 240ms ease",
                transitionDelay: `${delay}ms`,
              }}
            />
          );
        })}
      </svg>

      {ids.map((id, i) => {
        const node = nodeById.get(id);
        const pos = positions.get(id);
        if (!node || !pos) return null;
        const loc = place(pos);
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
              left: loc.left,
              top: loc.top,
              opacity: appear ? (isAssigned ? 0.6 : 1) : 0,
              transform: `translate(-50%, -50%) scale(${appear ? 1 : 0.4})`,
              transition: "opacity 220ms ease, transform 260ms cubic-bezier(0.34, 1.56, 0.64, 1)",
              transitionDelay: `${i * STAGGER}ms`,
            }}
            className={`absolute flex max-w-[150px] flex-col items-center gap-1 rounded-xl border px-2.5 py-1.5 shadow-sm ${
              isAssigned
                ? "cursor-default border-dashed border-gray-300 bg-gray-100"
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
            <span className="text-[9px] font-semibold tabular-nums text-[#999] whitespace-nowrap">
              {weekRange(node.first_week, node.last_week)}
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
