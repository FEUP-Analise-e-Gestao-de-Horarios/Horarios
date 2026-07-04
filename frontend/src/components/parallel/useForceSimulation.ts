import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent, RefObject } from "react";
import type { ParallelCandidateEdge, UUID } from "@/types/parallelSessions";
import type { NodePosition } from "./parallelGraph";

/** Coulomb-style repulsion strength between every pair of nodes. */
const REPULSION = 16000;
/** Hooke spring stiffness pulling edge endpoints toward `linkDistance`. */
const SPRING = 0.03;
/** Gentle pull toward the container centre so the graph never drifts away. */
const CENTER_PULL = 0.012;
/** Strong pull drawing selected nodes to the centre, so the rest circle them. */
const SELECT_PULL = 0.09;
/** Centre pull on non-selected nodes while a selection exists (lets them orbit). */
const ORBIT_PULL_FACTOR = 0.45;
/** Velocity retained each frame (1 = frictionless). */
const DAMPING = 0.82;
/** Per-frame speed cap, guards against the integrator exploding. */
const MAX_SPEED = 28;
/** Below this max speed the simulation is considered at rest and pauses. */
const REST_SPEED = 0.05;
/** Extra clear space enforced between two nodes on top of their radii. */
const COLLIDE_GAP = 14;
/** Radius used for a node whose measured size isn't known yet. */
const DEFAULT_RADIUS = 36;
/** Keep nodes this far inside the container edges. */
const MARGIN = 44;
/** Pointer travel (px) under which a press counts as a tap, not a drag. */
const TAP_SLOP = 4;
/**
 * Max synchronous steps run when the sim is (re)built, settling the seed
 * layout under the live forces before anything is visible. The seed is a crude
 * circle placement that isn't at rest under the live forces, so without this
 * it relaxes on screen: nodes sit still for a moment (velocities start at 0)
 * and then drift seconds into viewing the graph.
 * Generous on purpose — some seeds crawl through a near-equilibrium saddle
 * for hundreds of ticks before settling, and a warm-up that stops there
 * resumes as visible drift. The loop breaks at rest, so typical graphs only
 * pay a few hundred iterations; even the cap costs mere milliseconds at
 * these node counts.
 */
const WARMUP_TICKS = 5000;
/** Consecutive at-rest warm-up ticks required before the settle is trusted. */
const WARMUP_REST_STREAK = 10;

// Shake-to-scream easter egg: whip a held node hard enough back and forth and
// something plays. "Hard" = several fast direction reversals in a short window.
/** A move shorter than this (px between events) is too gentle to count. */
const SHAKE_MIN_STEP = 6;
/** Rolling window (ms) over which reversals are tallied. */
const SHAKE_WINDOW = 800;
/** Reversals within the window that make a shake count as "really hard". */
const SHAKE_REVERSALS = 4;
/** Minimum gap (ms) between triggers, so one frenzy fires exactly once. */
const SHAKE_COOLDOWN = 1200;

interface Layout {
  initial: Map<UUID, NodePosition>;
  width: number;
  height: number;
  linkDistance: number;
}

interface SimState {
  ids: UUID[];
  index: Map<UUID, number>;
  x: number[];
  y: number[];
  vx: number[];
  vy: number[];
  /** Per-node collision radius — bigger nodes claim more space. */
  r: number[];
  edges: [number, number][];
  width: number;
  height: number;
  link: number;
  dragIdx: number | null;
  dragX: number;
  dragY: number;
  /** Indices of selected nodes — pulled hard to the centre. */
  anchorIdx: Set<number>;
}

export interface ForceSimulation {
  positions: Map<UUID, NodePosition>;
  draggingId: UUID | null;
  onNodePointerDown: (id: UUID, e: ReactPointerEvent) => void;
}

/**
 * Advance the simulation one frame in place: apply repulsion, springs and
 * centre pull, integrate, then positionally resolve collisions. Returns the
 * frame's peak speeds so callers can decide whether the system is at rest.
 */
function stepSim(s: SimState): { maxSpeed: number; collMove: number } {
  const n = s.x.length;
  const fx = new Array<number>(n).fill(0);
  const fy = new Array<number>(n).fill(0);
  const cx = s.width / 2;
  const cy = s.height / 2;

  // Pairwise repulsion (O(n^2) — graphs here are small).
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      let dx = s.x[i]! - s.x[j]!;
      let dy = s.y[i]! - s.y[j]!;
      let d2 = dx * dx + dy * dy;
      if (d2 < 0.01) {
        dx = i - j || 1;
        dy = 1;
        d2 = dx * dx + dy * dy;
      }
      const d = Math.sqrt(d2);
      const f = REPULSION / d2;
      const ux = dx / d;
      const uy = dy / d;
      fx[i]! += ux * f;
      fy[i]! += uy * f;
      fx[j]! -= ux * f;
      fy[j]! -= uy * f;
    }
  }

  // Edge springs pull endpoints toward the rest length.
  for (const [ia, ib] of s.edges) {
    const dx = s.x[ib]! - s.x[ia]!;
    const dy = s.y[ib]! - s.y[ia]!;
    const d = Math.hypot(dx, dy) || 0.01;
    // Rest length grows with both endpoints' radii so larger nodes sit further apart.
    const rest = s.link + s.r[ia]! + s.r[ib]!;
    const f = SPRING * (d - rest);
    const ux = dx / d;
    const uy = dy / d;
    fx[ia]! += ux * f;
    fy[ia]! += uy * f;
    fx[ib]! -= ux * f;
    fy[ib]! -= uy * f;
  }

  // Centre pull. With a selection, selected nodes are pulled hard to the
  // centre while the rest are held loosely, so they fan out and circle.
  const hasAnchor = s.anchorIdx.size > 0;
  for (let i = 0; i < n; i++) {
    const pull = hasAnchor
      ? s.anchorIdx.has(i)
        ? SELECT_PULL
        : CENTER_PULL * ORBIT_PULL_FACTOR
      : CENTER_PULL;
    fx[i]! += (cx - s.x[i]!) * pull;
    fy[i]! += (cy - s.y[i]!) * pull;
  }

  // Integrate.
  let maxSpeed = 0;
  for (let i = 0; i < n; i++) {
    if (i === s.dragIdx) {
      s.x[i] = s.dragX;
      s.y[i] = s.dragY;
      s.vx[i] = 0;
      s.vy[i] = 0;
      continue;
    }
    let vx = (s.vx[i]! + fx[i]!) * DAMPING;
    let vy = (s.vy[i]! + fy[i]!) * DAMPING;
    const sp = Math.hypot(vx, vy);
    if (sp > MAX_SPEED) {
      vx = (vx / sp) * MAX_SPEED;
      vy = (vy / sp) * MAX_SPEED;
    }
    s.vx[i] = vx;
    s.vy[i] = vy;
    s.x[i] = Math.max(MARGIN, Math.min(s.width - MARGIN, s.x[i]! + vx));
    s.y[i] = Math.max(MARGIN, Math.min(s.height - MARGIN, s.y[i]! + vy));
    if (sp > maxSpeed) maxSpeed = sp;
  }

  // Collision: positionally separate any two nodes closer than their combined
  // radii (+ gap). This is what makes spacing scale with node size and keeps
  // boxes from overlapping. A dragged node is immovable — the other yields.
  let collMove = 0;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      let dx = s.x[i]! - s.x[j]!;
      let dy = s.y[i]! - s.y[j]!;
      let dist = Math.hypot(dx, dy);
      const minDist = s.r[i]! + s.r[j]! + COLLIDE_GAP;
      if (dist >= minDist) continue;
      if (dist < 1e-3) {
        dx = i - j || 1;
        dy = 1;
        dist = Math.hypot(dx, dy);
      }
      const push = minDist - dist;
      const ux = dx / dist;
      const uy = dy / dist;
      if (i === s.dragIdx) {
        s.x[j] = s.x[j]! - ux * push;
        s.y[j] = s.y[j]! - uy * push;
      } else if (j === s.dragIdx) {
        s.x[i] = s.x[i]! + ux * push;
        s.y[i] = s.y[i]! + uy * push;
      } else {
        s.x[i] = s.x[i]! + ux * push * 0.5;
        s.y[i] = s.y[i]! + uy * push * 0.5;
        s.x[j] = s.x[j]! - ux * push * 0.5;
        s.y[j] = s.y[j]! - uy * push * 0.5;
      }
      if (push > collMove) collMove = push;
    }
  }
  // Re-clamp after the collision shoves.
  for (let i = 0; i < n; i++) {
    if (i === s.dragIdx) continue;
    s.x[i] = Math.max(MARGIN, Math.min(s.width - MARGIN, s.x[i]!));
    s.y[i] = Math.max(MARGIN, Math.min(s.height - MARGIN, s.y[i]!));
  }

  return { maxSpeed, collMove };
}

/** True when a frame's peak movement is small enough to park the loop. */
function atRest(maxSpeed: number, collMove: number): boolean {
  return maxSpeed <= REST_SPEED && collMove <= REST_SPEED;
}

/** Snapshot the simulation's positions into a fresh id-keyed map. */
function snapshotPositions(s: SimState): Map<UUID, NodePosition> {
  const map = new Map<UUID, NodePosition>();
  for (let i = 0; i < s.ids.length; i++) map.set(s.ids[i]!, { x: s.x[i]!, y: s.y[i]! });
  return map;
}

/**
 * Live Fruchterman–Reingold-style simulation: nodes repel each other, edges act
 * as springs, and a node can be dragged (it pins to the pointer while its
 * neighbours are shoved aside and relax back). The loop is lazy — it only spins
 * the rAF while dragging or settling, then parks itself until the next drag.
 */
export function useForceSimulation(
  ids: UUID[],
  edges: ParallelCandidateEdge[],
  layout: Layout,
  radii: Map<UUID, number>,
  selected: Set<UUID>,
  onTap: (id: UUID) => void,
  containerRef: RefObject<HTMLElement | null>,
  onShake?: () => void,
): ForceSimulation {
  const [positions, setPositions] = useState<Map<UUID, NodePosition>>(
    () => new Map(layout.initial),
  );
  const [draggingId, setDraggingId] = useState<UUID | null>(null);

  const sim = useRef<SimState | null>(null);
  const rafRef = useRef<number | null>(null);
  const runningRef = useRef(false);
  const onTapRef = useRef(onTap);
  const onShakeRef = useRef(onShake);
  // Gesture state for the shake detector: last pointer position, last movement
  // vector (to spot direction reversals), reversal timestamps, and a cooldown.
  const shakeRef = useRef({
    lastX: 0,
    lastY: 0,
    vx: 0,
    vy: 0,
    reversals: [] as number[],
    lastFired: 0,
  });
  const selectedRef = useRef(selected);
  const radiiRef = useRef(radii);
  const pressRef = useRef<{ id: UUID; clientX: number; clientY: number; moved: boolean } | null>(
    null,
  );

  // Mirror the latest props into refs so the long-lived callbacks and effects
  // below read fresh values without depending on them. Declared before those
  // effects so it runs first within each commit.
  useEffect(() => {
    onTapRef.current = onTap;
    onShakeRef.current = onShake;
    selectedRef.current = selected;
    radiiRef.current = radii;
  });

  const tick = useCallback(
    // Named so the frame can schedule itself with rAF.
    function tickFrame() {
      const s = sim.current;
      if (!s) {
        runningRef.current = false;
        return;
      }
      const { maxSpeed, collMove } = stepSim(s);
      setPositions(snapshotPositions(s));

      if (s.dragIdx != null || !atRest(maxSpeed, collMove)) {
        rafRef.current = requestAnimationFrame(tickFrame);
      } else {
        runningRef.current = false;
      }
    },
    [],
  );

  const kick = useCallback(() => {
    if (runningRef.current) return;
    runningRef.current = true;
    rafRef.current = requestAnimationFrame(tick);
  }, [tick]);

  // (Re)build the physics state whenever the graph identity changes. `layout`,
  // `ids` and `edges` are all memoised upstream, so this runs once per graph.
  useEffect(() => {
    const n = ids.length;
    const index = new Map<UUID, number>();
    const x = new Array<number>(n);
    const y = new Array<number>(n);
    const r = new Array<number>(n);
    ids.forEach((id, i) => {
      index.set(id, i);
      const p = layout.initial.get(id) ?? { x: layout.width / 2, y: layout.height / 2 };
      x[i] = p.x;
      y[i] = p.y;
      r[i] = radiiRef.current.get(id) ?? DEFAULT_RADIUS;
    });
    const edgeIdx: [number, number][] = [];
    for (const { source: a, target: b } of edges) {
      const ia = index.get(a);
      const ib = index.get(b);
      if (ia != null && ib != null) edgeIdx.push([ia, ib]);
    }
    const anchorIdx = new Set<number>();
    for (const id of selectedRef.current) {
      const i = index.get(id);
      if (i != null) anchorIdx.add(i);
    }
    const state: SimState = {
      ids: ids.slice(),
      index,
      x,
      y,
      vx: new Array<number>(n).fill(0),
      vy: new Array<number>(n).fill(0),
      r,
      edges: edgeIdx,
      width: layout.width,
      height: layout.height,
      link: layout.linkDistance,
      dragIdx: null,
      dragX: 0,
      dragY: 0,
      anchorIdx,
    };
    // Settle the seed layout under the live forces before it is ever shown —
    // the seed is a crude circle placement that isn't at rest under these
    // forces, so without this warm-up it relaxes on screen as a slow,
    // delayed-looking drift. Rest must hold for several consecutive ticks: near
    // a saddle the speed can dip under the threshold for a frame and then grow
    // again.
    let restStreak = 0;
    for (let i = 0; i < WARMUP_TICKS && restStreak < WARMUP_REST_STREAK; i++) {
      const { maxSpeed, collMove } = stepSim(state);
      restStreak = atRest(maxSpeed, collMove) ? restStreak + 1 : 0;
    }
    sim.current = state;
    setPositions(snapshotPositions(state));
  }, [ids, edges, layout]);

  // Re-anchor and re-settle whenever the selection changes: selected nodes are
  // drawn to the centre and the rest circle out around them.
  const selectionKey = useMemo(() => Array.from(selected).sort().join(","), [selected]);
  useEffect(() => {
    const s = sim.current;
    if (!s) return;
    const next = new Set<number>();
    for (const id of selectedRef.current) {
      const i = s.index.get(id);
      if (i != null) next.add(i);
    }
    s.anchorIdx = next;
    kick();
    // kick is stable; selectionKey captures the meaningful change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectionKey]);

  // Apply measured/estimated node radii in place and re-settle when they change.
  const radiiKey = useMemo(
    () => ids.map((id) => Math.round(radii.get(id) ?? DEFAULT_RADIUS)).join(","),
    [ids, radii],
  );
  useEffect(() => {
    const s = sim.current;
    if (!s) return;
    for (let i = 0; i < s.ids.length; i++) {
      s.r[i] = radiiRef.current.get(s.ids[i]!) ?? DEFAULT_RADIUS;
    }
    kick();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [radiiKey]);

  const pointFromEvent = useCallback(
    (clientX: number, clientY: number) => {
      const rect = containerRef.current?.getBoundingClientRect();
      const s = sim.current;
      if (!rect || !s) return null;
      // The container may be rendered scaled-to-fit, so its on-screen size differs
      // from the simulation's logical size. Map screen pixels back to logical space.
      const scaleX = rect.width ? rect.width / s.width : 1;
      const scaleY = rect.height ? rect.height / s.height : 1;
      return {
        x: Math.max(MARGIN, Math.min(s.width - MARGIN, (clientX - rect.left) / scaleX)),
        y: Math.max(MARGIN, Math.min(s.height - MARGIN, (clientY - rect.top) / scaleY)),
      };
    },
    [containerRef],
  );

  const onNodePointerDown = useCallback(
    (id: UUID, e: ReactPointerEvent) => {
      const s = sim.current;
      if (!s) return;
      const idx = s.index.get(id);
      if (idx == null) return;
      const pt = pointFromEvent(e.clientX, e.clientY);
      if (pt) {
        s.dragX = pt.x;
        s.dragY = pt.y;
      }
      s.dragIdx = idx;
      pressRef.current = { id, clientX: e.clientX, clientY: e.clientY, moved: false };
      // Reset the shake gesture for this new grab (keep the cooldown running).
      const sh = shakeRef.current;
      sh.lastX = e.clientX;
      sh.lastY = e.clientY;
      sh.vx = 0;
      sh.vy = 0;
      sh.reversals.length = 0;
      setDraggingId(id);
      kick();
    },
    [kick, pointFromEvent],
  );

  // Window-level drag tracking while a node is held.
  useEffect(() => {
    if (draggingId == null) return;
    const move = (e: PointerEvent) => {
      const s = sim.current;
      const press = pressRef.current;
      if (!s) return;
      if (press && !press.moved) {
        if (Math.hypot(e.clientX - press.clientX, e.clientY - press.clientY) > TAP_SLOP) {
          press.moved = true;
        }
      }
      // Shake detector: a fast move roughly opposite the previous fast move is a
      // reversal; enough reversals in the window fires the scream (once, then a
      // cooldown). Gentle dragging never reverses hard enough to count.
      if (onShakeRef.current) {
        const sh = shakeRef.current;
        const now = performance.now();
        const dx = e.clientX - sh.lastX;
        const dy = e.clientY - sh.lastY;
        sh.lastX = e.clientX;
        sh.lastY = e.clientY;
        if (Math.hypot(dx, dy) >= SHAKE_MIN_STEP) {
          if (dx * sh.vx + dy * sh.vy < 0) {
            sh.reversals.push(now);
            while (sh.reversals.length && now - sh.reversals[0]! > SHAKE_WINDOW) {
              sh.reversals.shift();
            }
            if (sh.reversals.length >= SHAKE_REVERSALS && now - sh.lastFired > SHAKE_COOLDOWN) {
              sh.lastFired = now;
              sh.reversals.length = 0;
              onShakeRef.current();
            }
          }
          sh.vx = dx;
          sh.vy = dy;
        }
      }
      const pt = pointFromEvent(e.clientX, e.clientY);
      if (pt) {
        s.dragX = pt.x;
        s.dragY = pt.y;
      }
      kick();
    };
    const up = () => {
      const s = sim.current;
      const press = pressRef.current;
      if (s) s.dragIdx = null;
      if (press && !press.moved) onTapRef.current(press.id);
      pressRef.current = null;
      setDraggingId(null);
      kick();
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
  }, [draggingId, kick, pointFromEvent]);

  // Stop the loop on unmount.
  useEffect(() => {
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      runningRef.current = false;
    };
  }, []);

  return { positions, draggingId, onNodePointerDown };
}
