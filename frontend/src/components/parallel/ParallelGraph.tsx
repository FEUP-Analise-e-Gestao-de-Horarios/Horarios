import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ParallelBlockNode, ParallelCandidateGraph, UUID } from "@/types/parallelSessions";
import GraphInspector, { type HoverTarget } from "./GraphInspector";
import { buildAdjacency } from "./parallelGraph";
import { useForceSimulation } from "./useForceSimulation";

interface ParallelGraphProps {
  graph: ParallelCandidateGraph;
  /** Blocks the user has currently selected to form a new group. */
  selected: Set<UUID>;
  /** Blocks already assigned to a (draft or confirmed) group — locked. */
  assigned: Set<UUID>;
  onToggleNode: (blockId: UUID) => void;
  /** Tap on an already-grouped node — reveals its group in the side panel. */
  onTapAssigned?: (blockId: UUID) => void;
  sessionTypeStyle: (type: string) => { bg: string; text: string };
}

const NODE_PAD = 84;
const LINK_DISTANCE = 140;
/** Widest a node box can render (Tailwind max-w-[150px]). */
const NODE_MAX_W = 150;

/** User-zoom bounds, applied on top of the fit-to-container scale. */
const MIN_ZOOM = 1;
const MAX_ZOOM = 3.5;
/** Start noticeably more zoomed-in than a plain fit, so small graphs don't open
 * tiny and need a manual zoom-in. */
const DEFAULT_ZOOM = 2.5;
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

/** Invisible stroke width making thin edges hoverable. */
const EDGE_HIT_WIDTH = 16;

/**
 * Web Audio backing for the goat-scream easter egg. The mp3 bytes are fetched
 * and decoded a single time for the page's lifetime into an AudioBuffer; each
 * scream then plays a throwaway AudioBufferSourceNode off that cached buffer, so
 * there is no per-play network fetch and overlapping screams stack into a chorus
 * for free. Everything is lazy — nothing is constructed at import time, so
 * importing this module under SSR/jsdom (no AudioContext) never throws.
 */
const GOAT_SCREAM_VOLUME = 0.75;
let goatAudioContext: AudioContext | null = null;
let goatBufferPromise: Promise<AudioBuffer> | null = null;

function getGoatAudioContext(): AudioContext {
  if (!goatAudioContext) {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    goatAudioContext = new Ctor();
  }
  return goatAudioContext;
}

/** Fetch + decode the mp3 once, caching the in-flight promise so rapid screams
 * before the first decode finishes don't kick off duplicate loads. A failed
 * load (missing file, transient network error, decode failure) clears the cache
 * so a later scream retries instead of staying silent for the page's lifetime. */
function ensureGoatBuffer(ctx: AudioContext): Promise<AudioBuffer> {
  if (!goatBufferPromise) {
    goatBufferPromise = fetch(`${import.meta.env.BASE_URL}goat-scream.mp3`)
      .then((res) => res.arrayBuffer())
      .then((bytes) => ctx.decodeAudioData(bytes))
      .catch((err) => {
        goatBufferPromise = null;
        throw err;
      });
  }
  return goatBufferPromise;
}

export default function ParallelGraph({
  graph,
  selected,
  assigned,
  onToggleNode,
  onTapAssigned,
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

  // Cheap deterministic circle seed for the live simulation, laid out in a
  // generous square container that keeps a fixed size so dragging never reflows
  // the page. This isn't the final layout — it just gives the simulation a
  // sane, non-degenerate start; the warm-up settles it off-screen. The seed
  // spacing and padding grow with node size so the box is roomy enough for the
  // size-aware live layout to spread without hitting the sim's margin clamp.
  const layout = useMemo(() => {
    const seedLink = LINK_DISTANCE + 2 * meanRadius;
    const pad = NODE_PAD + maxRadius;
    const n = ids.length;
    // Radius of a circle whose circumference spaces n nodes ~seedLink apart,
    // then inflated by a safety factor so the live model has slack to spread.
    const r0 = n <= 1 ? 0 : seedLink * Math.max(1, n / (2 * Math.PI));
    const radius = r0 * 1.15;
    const size = 2 * (radius + pad);
    const center = size / 2;
    const initial = new Map<UUID, { x: number; y: number }>();
    if (n === 1) {
      initial.set(ids[0]!, { x: center, y: center });
    } else if (n === 2) {
      // A single pair reads best side by side (horizontal), not stacked.
      initial.set(ids[0]!, { x: center - radius, y: center });
      initial.set(ids[1]!, { x: center + radius, y: center });
    } else {
      for (let i = 0; i < n; i++) {
        const angle = (i * 2 * Math.PI) / n - Math.PI / 2;
        // The 2.399963 offset breaks perfect symmetry so nodes never start
        // coincident/collinear (which can trap them under the live forces).
        const x = center + Math.cos(angle) * radius + Math.cos(i * 2.399963) * 4;
        const y = center + Math.sin(angle) * radius + Math.sin(i * 2.399963) * 4;
        initial.set(ids[i]!, { x, y });
      }
    }
    return { initial, width: size, height: size, linkDistance: LINK_DISTANCE };
  }, [ids, meanRadius, maxRadius]);

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

  // What the mouse is over (node or edge), feeding the inspector card and the
  // hover highlights. Touch never sets it (no hover there — the card falls
  // back to the selection summary).
  const [hovered, setHovered] = useState<HoverTarget | null>(null);

  const hoveredNodeId = hovered?.kind === "node" ? hovered.id : null;
  const hoveredEdge = hovered?.kind === "edge" ? (graph.edges[hovered.index] ?? null) : null;

  // Heaviest collision in the graph, so edge strokes can scale relative to it.
  const maxEdgeWeeks = useMemo(
    () => graph.edges.reduce((max, e) => Math.max(max, e.weeks.length), 1),
    [graph.edges],
  );

  // A tap (a press that didn't turn into a drag) toggles a free node into the
  // selection, or — for a locked node — reveals the group it already belongs to.
  // Dimmed nodes (outside the active frontier) can't join the group, so a tap on
  // them is a no-op. Every node can still be dragged around regardless.
  const onTap = useCallback(
    (id: UUID) => {
      if (assigned.has(id)) onTapAssigned?.(id);
      else if (active === null || active.has(id)) onToggleNode(id);
    },
    [assigned, onToggleNode, onTapAssigned, active],
  );

  // Easter egg: shaking a held node really hard plays a goat scream. The audio
  // lives at public/goat-scream.mp3 and is fetched + decoded a single time for
  // the page via Web Audio (see ensureGoatBuffer); every scream then fires a
  // throwaway source node off that cached buffer, so there's no per-play fetch
  // and overlapping shakes stack into a chorus. The first scream carries a tiny
  // one-time decode delay; the rest are instant. Any failure (missing file,
  // decode error, no Web Audio support) is swallowed — the gesture stays silent.
  const playGoatScream = useCallback(() => {
    try {
      const ctx = getGoatAudioContext();
      if (ctx.state === "suspended") void ctx.resume();
      void ensureGoatBuffer(ctx)
        .then((buffer) => {
          const source = ctx.createBufferSource();
          source.buffer = buffer;
          const gain = ctx.createGain();
          gain.gain.value = GOAT_SCREAM_VOLUME;
          source.connect(gain).connect(ctx.destination);
          source.start(0);
        })
        .catch(() => {});
    } catch {
      // No Web Audio support (or context construction failed) — stay silent.
    }
  }, []);

  const { positions, draggingId, onNodePointerDown } = useForceSimulation(
    ids,
    graph.edges,
    layout,
    radii,
    selected,
    onTap,
    containerRef,
    playGoatScream,
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

  // The inspector's home is the graph's bottom-left corner. Hovering a node or
  // edge that sits under the card slides it up to the top-left corner;
  // hovering anything clear of the home spot slides it back down. The hovered
  // target's rect is captured on pointer enter, and the overlap decision runs
  // *after* the card renders for that target, so it measures the card's real
  // size (a first hover has nothing on screen to measure at enter time). The
  // check always uses the card's *home* rect, so a dodged card knows when its
  // spot is free again.
  const [dodged, setDodged] = useState(false);
  const inspectorRef = useRef<HTMLDivElement>(null);
  const hoverTargetRect = useRef<{
    left: number;
    right: number;
    top: number;
    bottom: number;
  } | null>(null);
  useLayoutEffect(() => {
    const target = hoverTargetRect.current;
    const vp = viewportRef.current?.getBoundingClientRect();
    // Pure translation, so the rect keeps the card's size in either position.
    const card = inspectorRef.current?.getBoundingClientRect();
    if (!target || !vp || !card || card.height === 0) {
      setDodged(false);
      return;
    }
    const margin = 8;
    const home = {
      left: vp.left + margin,
      right: vp.left + margin + card.width,
      top: vp.bottom - margin - card.height,
      bottom: vp.bottom - margin,
    };
    setDodged(
      target.left < home.right &&
        target.right > home.left &&
        target.top < home.bottom &&
        target.bottom > home.top,
    );
  }, [hovered]);

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
      <div className="absolute right-2 top-2 z-20 flex flex-col overflow-hidden rounded-lg border border-[#e2e2e2] bg-white/90 shadow-sm backdrop-blur">
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
        ref={inspectorRef}
        className="pointer-events-none absolute bottom-2 left-2 z-20 transition-transform duration-300 ease-out"
        style={{
          // Dodged, the card's top edge lands on the viewport's top inset:
          // 100% cancels its own height, then it shifts up by the viewport
          // height minus both 8px insets.
          transform:
            dodged && viewport
              ? `translateY(calc(100% - ${Math.round(viewport.h) - 16}px))`
              : "translateY(0)",
        }}
      >
        <GraphInspector
          graph={graph}
          nodeById={nodeById}
          hovered={hovered}
          selected={selected}
          assigned={assigned}
          active={active}
          sessionTypeStyle={sessionTypeStyle}
        />
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
              if (!pa || !pb) return null;
              const bothSelected = selected.has(a) && selected.has(b);
              // An edge is "connected to the selection" when either endpoint is
              // selected; otherwise it is dimmed.
              const edgeActive = active === null || selected.has(a) || selected.has(b);
              const isHovered =
                (hovered?.kind === "edge" && hovered.index === i) ||
                hoveredNodeId === a ||
                hoveredNodeId === b;
              // Collision strength drives the stroke: pairs that collide on more
              // weeks draw heavier lines.
              const width = 1 + 2 * (weeks.length / maxEdgeWeeks);
              const delay =
                (Math.max(orderIndex.get(a) ?? 0, orderIndex.get(b) ?? 0) + 1) * STAGGER;
              return (
                <g
                  key={`${a}-${b}-${i}`}
                  style={{
                    opacity: appear ? (edgeActive ? 1 : 0.18) : 0,
                    // Longhand instead of the `transition` shorthand: React warns
                    // when a shorthand and `transitionDelay` mix on one element.
                    transitionProperty: "opacity",
                    transitionDuration: "240ms",
                    transitionTimingFunction: "ease",
                    transitionDelay: `${appear ? 0 : delay}ms`,
                  }}
                >
                  <line
                    x1={pa.x}
                    y1={pa.y}
                    x2={pb.x}
                    y2={pb.y}
                    stroke={bothSelected ? "#f59e0b" : isHovered ? "#6b7280" : "#d1d5db"}
                    strokeWidth={bothSelected || isHovered ? width + 1 : width}
                  />
                  {/* Generous invisible hit target — the visible line is unhoverable. */}
                  <line
                    x1={pa.x}
                    y1={pa.y}
                    x2={pb.x}
                    y2={pb.y}
                    stroke="transparent"
                    strokeWidth={EDGE_HIT_WIDTH}
                    style={{ pointerEvents: "stroke" }}
                    onPointerEnter={(e) => {
                      if (e.pointerType !== "mouse") return;
                      hoverTargetRect.current = {
                        left: e.clientX - 6,
                        right: e.clientX + 6,
                        top: e.clientY - 6,
                        bottom: e.clientY + 6,
                      };
                      setHovered({ kind: "edge", index: i });
                    }}
                    onPointerLeave={(e) => {
                      if (e.pointerType !== "mouse") return;
                      hoverTargetRect.current = null;
                      setHovered(null);
                    }}
                  />
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
            // Emphasised as the far end of what's hovered: an endpoint of a
            // hovered edge, or a neighbour of a hovered node.
            const isHoverRelated =
              (hoveredEdge !== null && (hoveredEdge.source === id || hoveredEdge.target === id)) ||
              (hoveredNodeId !== null &&
                hoveredNodeId !== id &&
                (adjacency.get(hoveredNodeId)?.has(id) ?? false));
            const typeStyle = sessionTypeStyle(node.session.type);
            const codes = node.classes.map((c) => c.code).join(" ");
            return (
              <button
                key={id}
                type="button"
                onPointerDown={(e) => onNodePointerDown(id, e)}
                onPointerEnter={(e) => {
                  if (e.pointerType !== "mouse") return;
                  hoverTargetRect.current = e.currentTarget.getBoundingClientRect();
                  setHovered({ kind: "node", id });
                }}
                onPointerLeave={(e) => {
                  if (e.pointerType !== "mouse") return;
                  hoverTargetRect.current = null;
                  setHovered(null);
                }}
                style={{
                  left: pos.x,
                  top: pos.y,
                  opacity: appear ? (isDimmed ? 0.3 : isAssigned ? 0.6 : 1) : 0,
                  filter: isDimmed ? "grayscale(1)" : undefined,
                  transform: `translate(-50%, -50%) scale(${appear ? (isDragging ? 1.08 : 1) : 0.4})`,
                  // Position is driven by the physics loop, so it must not transition;
                  // only the entrance/drag scale, opacity and dimming animate. Written
                  // longhand because React warns when the `transition` shorthand and
                  // `transitionDelay` mix on one element.
                  transitionProperty: appear ? "transform, opacity, filter" : "opacity, transform",
                  transitionDuration: appear ? "120ms, 220ms, 220ms" : "220ms, 260ms",
                  transitionTimingFunction: appear
                    ? "ease"
                    : "ease, cubic-bezier(0.34, 1.56, 0.64, 1)",
                  transitionDelay: appear ? "0ms" : `${i * STAGGER}ms`,
                  cursor: isDragging ? "grabbing" : isAssigned ? "grab" : "grab",
                  zIndex: isDragging ? 10 : undefined,
                }}
                className={`absolute flex max-w-[150px] touch-none flex-col items-center gap-1 rounded-xl border px-2.5 py-1.5 shadow-sm ${
                  isAssigned
                    ? `border-dashed bg-gray-100 ${isHoverRelated ? "border-gray-400" : "border-gray-300"}`
                    : isSelected
                      ? "border-amber-400 bg-amber-50 ring-2 ring-amber-300"
                      : isHoverRelated
                        ? "border-gray-500 bg-white"
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
