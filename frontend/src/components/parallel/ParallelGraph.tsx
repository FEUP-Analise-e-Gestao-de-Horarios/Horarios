import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ParallelBlockNode, ParallelCandidateGraph, UUID } from "@/types/parallelSessions";
import { buildAdjacency, forceLayout } from "./parallelGraph";
import { useForceSimulation } from "./useForceSimulation";

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
const LINK_DISTANCE = 140;
/** Widest a node box can render (Tailwind max-w-[150px]). */
const NODE_MAX_W = 150;

/** User-zoom bounds, applied on top of the fit-to-container scale. */
const MIN_ZOOM = 0.4;
const MAX_ZOOM = 3;
/** Start a touch more zoomed-in than a plain fit. */
const DEFAULT_ZOOM = 1.25;
const ZOOM_STEP = 1.2;

function clampZoom(z: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));
}

/**
 * Approximate a node's collision radius from its content, so spacing can scale
 * with size without waiting on a DOM measure. Width tracks the class-code text
 * (capped at the box max-width); height is roughly constant.
 */
function estimateRadius(codes: string): number {
  const width = Math.min(NODE_MAX_W, Math.max(58, codes.length * 6.2 + 24));
  return 0.5 * Math.hypot(width, 56);
}
/** Per-node delay of the entrance burst, in ms. */
const STAGGER = 45;

/** Format an ISO date (YYYY-MM-DD) as DD/MM. */
function formatWeek(dateStr: string): string {
  const parts = dateStr.split("-");
  return parts.length === 3 ? `${parts[2]}/${parts[1]}` : dateStr;
}

/** A week span, e.g. "15/09" or "15/09–20/12". */
function weekRange(first: string, last: string): string {
  const a = formatWeek(first);
  const b = formatWeek(last);
  return a === b ? a : `${a}–${b}`;
}

/**
 * The exact weeks two blocks collide on — the reason an edge exists. The label
 * is the span of those weeks; the tooltip carries the precise list (collisions
 * can be non-contiguous, e.g. biweekly). ISO dates sort lexically.
 */
function edgeWeeksLabel(weeks: string[]): { range: string; tooltip: string } {
  if (weeks.length === 0) return { range: "", tooltip: "" };
  const sorted = [...weeks].sort();
  const range = weekRange(sorted[0]!, sorted[sorted.length - 1]!);
  const tooltip =
    sorted.length === 1
      ? `1 semana: ${formatWeek(sorted[0]!)}`
      : `${sorted.length} semanas: ${sorted.map(formatWeek).join(", ")}`;
  return { range, tooltip };
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

  // Per-node collision radius, derived from the class-code text length.
  const radii = useMemo(() => {
    const map = new Map<UUID, number>();
    for (const node of graph.nodes) {
      const codes = node.classes.map((c) => c.code).join(" ");
      map.set(node.original_block_id, estimateRadius(codes));
    }
    return map;
  }, [graph.nodes]);

  const { meanRadius, maxRadius } = useMemo(() => {
    let sum = 0;
    let max = 0;
    for (const r of radii.values()) {
      sum += r;
      if (r > max) max = r;
    }
    return { meanRadius: radii.size ? sum / radii.size : 40, maxRadius: max };
  }, [radii]);

  // One-shot relaxed layout, then translated into container coordinates. This
  // seeds the live simulation; the container keeps this fixed size so dragging
  // never reflows the page. The seed spacing and padding grow with node size so
  // the box is roomy enough for the size-aware live layout.
  const layout = useMemo(() => {
    const seedLink = LINK_DISTANCE + 2 * meanRadius;
    const raw = forceLayout(ids, graph.edges, { linkDistance: seedLink });
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const p of raw.values()) {
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    }
    if (!Number.isFinite(minX)) {
      minX = minY = maxX = maxY = 0;
    }
    const pad = NODE_PAD + maxRadius;
    const width = maxX - minX + pad * 2;
    const height = maxY - minY + pad * 2;
    const initial = new Map<UUID, { x: number; y: number }>();
    for (const [id, p] of raw) {
      initial.set(id, { x: p.x - minX + pad, y: p.y - minY + pad });
    }
    // Seed uses the radius-inflated spacing, but the live springs add each
    // edge's own radii on top, so they keep the plain base rest length. On
    // average these agree, so the graph barely moves on load.
    return { initial, width, height, linkDistance: LINK_DISTANCE };
  }, [ids, graph.edges, meanRadius, maxRadius]);

  const containerRef = useRef<HTMLDivElement>(null);

  const adjacency = useMemo(() => buildAdjacency(graph.edges), [graph.edges]);

  // Nodes in play while building a group: the selection plus everything one edge
  // away from it. This frontier grows as more nodes are selected; anything
  // outside it is dimmed. Null means "no selection" — nothing is dimmed.
  const active = useMemo(() => {
    if (selected.size === 0) return null;
    const set = new Set<UUID>(selected);
    for (const id of selected) {
      for (const neighbor of adjacency.get(id) ?? []) set.add(neighbor);
    }
    return set;
  }, [selected, adjacency]);

  // Toggle only fires on a tap (a press that didn't turn into a drag), and never
  // for locked nodes — but every node can still be dragged around.
  const onTap = useCallback(
    (id: UUID) => {
      if (!assigned.has(id)) onToggleNode(id);
    },
    [assigned, onToggleNode],
  );

  const { positions, draggingId, onNodePointerDown } = useForceSimulation(
    ids,
    graph.edges,
    layout,
    radii,
    selected,
    onTap,
    containerRef,
  );

  // Entrance burst: nodes pop in sequence once the graph mounts.
  const [appear, setAppear] = useState(false);
  useEffect(() => {
    const raf = requestAnimationFrame(() => setAppear(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  // Fit-to-container: measure the available area and scale the fixed-size graph
  // down so it always fits without scrolling. Never upscale past natural size.
  const viewportRef = useRef<HTMLDivElement>(null);
  const [viewport, setViewport] = useState<{ w: number; h: number } | null>(null);
  useLayoutEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const measure = () => {
      const rect = el.getBoundingClientRect();
      setViewport((prev) =>
        prev && prev.w === rect.width && prev.h === rect.height
          ? prev
          : { w: rect.width, h: rect.height },
      );
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Fit-to-container scale (never upscales past natural size), then the user's
  // own zoom on top so they can push in past the fit and pan by dragging nodes.
  const fitScale = viewport
    ? Math.min(1, viewport.w / layout.width, viewport.h / layout.height)
    : 1;
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);
  const scale = fitScale * zoom;

  const zoomBy = useCallback((factor: number) => {
    setZoom((z) => clampZoom(z * factor));
  }, []);

  // Wheel-to-zoom. Attached natively (non-passive) so preventDefault can stop
  // the page from scrolling while zooming over the graph.
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      setZoom((z) => clampZoom(z * Math.exp(-e.deltaY * 0.0015)));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  return (
    <div
      ref={viewportRef}
      className="relative flex h-full w-full items-center justify-center overflow-hidden"
    >
      <div className="absolute left-2 top-2 z-20 flex flex-col overflow-hidden rounded-lg border border-[#e2e2e2] bg-white/90 shadow-sm backdrop-blur">
        <button
          type="button"
          onClick={() => zoomBy(ZOOM_STEP)}
          title="Aproximar"
          className="flex h-7 w-7 items-center justify-center text-lg font-semibold leading-none text-[#555] hover:bg-[#f3f3f3] cursor-pointer"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => zoomBy(1 / ZOOM_STEP)}
          title="Afastar"
          className="flex h-7 w-7 items-center justify-center border-t border-[#eee] text-lg font-semibold leading-none text-[#555] hover:bg-[#f3f3f3] cursor-pointer"
        >
          −
        </button>
        <button
          type="button"
          onClick={() => setZoom(DEFAULT_ZOOM)}
          title="Repor zoom"
          className="flex h-7 w-7 items-center justify-center border-t border-[#eee] text-xs font-semibold leading-none text-[#777] hover:bg-[#f3f3f3] cursor-pointer"
        >
          ⤢
        </button>
      </div>
      <div
        className="relative shrink-0"
        style={{ width: layout.width * scale, height: layout.height * scale }}
      >
        <div
          ref={containerRef}
          className="absolute left-0 top-0 origin-top-left touch-none select-none"
          style={{ width: layout.width, height: layout.height, transform: `scale(${scale})` }}
        >
          <svg
            className="absolute inset-0 pointer-events-none"
            width={layout.width}
            height={layout.height}
            aria-hidden
          >
            {graph.edges.map(({ source: a, target: b, weeks }, i) => {
              const pa = positions.get(a);
              const pb = positions.get(b);
              const na = nodeById.get(a);
              const nb = nodeById.get(b);
              if (!pa || !pb || !na || !nb) return null;
              const { range: weeksRange, tooltip: weeksTooltip } = edgeWeeksLabel(weeks);
              const bothSelected = selected.has(a) && selected.has(b);
              // An edge is "connected to the selection" when either endpoint is
              // selected; otherwise its line and week range are dimmed.
              const edgeActive = active === null || selected.has(a) || selected.has(b);
              const delay =
                (Math.max(orderIndex.get(a) ?? 0, orderIndex.get(b) ?? 0) + 1) * STAGGER;
              const mx = (pa.x + pb.x) / 2;
              const my = (pa.y + pb.y) / 2;
              return (
                <g
                  key={`${a}-${b}-${i}`}
                  style={{
                    opacity: appear ? (edgeActive ? 1 : 0.18) : 0,
                    transition: "opacity 240ms ease",
                    transitionDelay: `${appear ? 0 : delay}ms`,
                  }}
                >
                  <line
                    x1={pa.x}
                    y1={pa.y}
                    x2={pb.x}
                    y2={pb.y}
                    stroke={bothSelected ? "#f59e0b" : "#d1d5db"}
                    strokeWidth={bothSelected ? 2.5 : 1.5}
                  />
                  <text
                    x={mx}
                    y={my}
                    textAnchor="middle"
                    dominantBaseline="central"
                    style={{
                      fontSize: 9,
                      fontWeight: 600,
                      fontVariantNumeric: "tabular-nums",
                      fill: bothSelected ? "#b45309" : "#9ca3af",
                      // White halo so the label stays legible over the edge line.
                      paintOrder: "stroke",
                      stroke: "#fff",
                      strokeWidth: 3,
                      strokeLinejoin: "round",
                    }}
                  >
                    <title>{weeksTooltip}</title>
                    {weeksRange}
                  </text>
                </g>
              );
            })}
          </svg>

          {ids.map((id, i) => {
            const node = nodeById.get(id);
            const pos = positions.get(id);
            if (!node || !pos) return null;
            const isAssigned = assigned.has(id);
            const isSelected = selected.has(id);
            const isDragging = draggingId === id;
            // Not selected and not adjacent to the selection: greyed out.
            const isDimmed = active !== null && !active.has(id);
            const typeStyle = sessionTypeStyle(node.session.type);
            const codes = node.classes.map((c) => c.code).join(" ");
            return (
              <button
                key={id}
                type="button"
                onPointerDown={(e) => onNodePointerDown(id, e)}
                title={isAssigned ? "Já pertence a um grupo" : codes}
                style={{
                  left: pos.x,
                  top: pos.y,
                  opacity: appear ? (isDimmed ? 0.3 : isAssigned ? 0.6 : 1) : 0,
                  filter: isDimmed ? "grayscale(1)" : undefined,
                  transform: `translate(-50%, -50%) scale(${appear ? (isDragging ? 1.08 : 1) : 0.4})`,
                  // Position is driven by the physics loop, so it must not transition;
                  // only the entrance/drag scale, opacity and dimming animate.
                  transition: appear
                    ? "transform 120ms ease, opacity 220ms ease, filter 220ms ease"
                    : "opacity 220ms ease, transform 260ms cubic-bezier(0.34, 1.56, 0.64, 1)",
                  transitionDelay: appear ? "0ms" : `${i * STAGGER}ms`,
                  cursor: isDragging ? "grabbing" : isAssigned ? "grab" : "grab",
                  zIndex: isDragging ? 10 : undefined,
                }}
                className={`absolute flex max-w-[150px] touch-none flex-col items-center gap-1 rounded-xl border px-2.5 py-1.5 shadow-sm ${
                  isAssigned
                    ? "border-dashed border-gray-300 bg-gray-100"
                    : isSelected
                      ? "border-amber-400 bg-amber-50 ring-2 ring-amber-300"
                      : "border-gray-300 bg-white hover:border-gray-400 hover:bg-[#fffdf5]"
                } ${isDragging ? "shadow-lg" : ""}`}
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
      </div>
    </div>
  );
}
