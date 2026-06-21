import type { UUID } from "@/types/parallelSessions";

/** Build an undirected adjacency map from an edge list. */
export function buildAdjacency(edges: [UUID, UUID][]): Map<UUID, Set<UUID>> {
  const adj = new Map<UUID, Set<UUID>>();
  const link = (a: UUID, b: UUID) => {
    let set = adj.get(a);
    if (!set) {
      set = new Set();
      adj.set(a, set);
    }
    set.add(b);
  };
  for (const [a, b] of edges) {
    link(a, b);
    link(b, a);
  }
  return adj;
}

/**
 * True when `selection` forms a connected subgraph of `adj` (every selected
 * node reachable from any other using only edges between selected nodes).
 * The empty set and singletons are trivially connected.
 */
export function isConnectedSelection(selection: Set<UUID>, adj: Map<UUID, Set<UUID>>): boolean {
  if (selection.size <= 1) return true;
  const start = selection.values().next().value as UUID;
  const seen = new Set<UUID>([start]);
  const stack = [start];
  while (stack.length > 0) {
    const cur = stack.pop() as UUID;
    for (const next of adj.get(cur) ?? []) {
      if (selection.has(next) && !seen.has(next)) {
        seen.add(next);
        stack.push(next);
      }
    }
  }
  return seen.size === selection.size;
}

export interface NodePosition {
  x: number;
  y: number;
}

/**
 * Deterministic force-directed (Fruchterman–Reingold) layout for a component's
 * nodes. Nodes start on a circle (so the result is stable across renders) and
 * relax under edge springs and node repulsion. Positions are centred on the
 * origin.
 */
export function forceLayout(
  ids: UUID[],
  edges: [UUID, UUID][],
  opts: { linkDistance?: number; iterations?: number } = {},
): Map<UUID, NodePosition> {
  const positions = new Map<UUID, NodePosition>();
  const n = ids.length;
  if (n === 0) return positions;
  if (n === 1) {
    positions.set(ids[0]!, { x: 0, y: 0 });
    return positions;
  }

  const k = opts.linkDistance ?? 120;
  const iterations = opts.iterations ?? 300;
  const k2 = k * k;

  // Deterministic initial layout on a circle.
  const r0 = k * Math.max(1, n / (2 * Math.PI));
  const xs = new Array<number>(n);
  const ys = new Array<number>(n);
  const index = new Map<UUID, number>();
  for (let i = 0; i < n; i++) {
    const id = ids[i]!;
    const angle = (i * 2 * Math.PI) / n - Math.PI / 2;
    xs[i] = Math.cos(angle) * r0;
    ys[i] = Math.sin(angle) * r0;
    index.set(id, i);
  }

  const dx = new Array<number>(n);
  const dy = new Array<number>(n);
  let temp = k;
  const cool = temp / (iterations + 1);

  for (let it = 0; it < iterations; it++) {
    for (let i = 0; i < n; i++) {
      dx[i] = 0;
      dy[i] = 0;
    }

    // Repulsion between every pair of nodes.
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const ddx = xs[i]! - xs[j]!;
        const ddy = ys[i]! - ys[j]!;
        const dist = Math.hypot(ddx, ddy) || 0.01;
        const force = k2 / dist;
        const ux = ddx / dist;
        const uy = ddy / dist;
        dx[i]! += ux * force;
        dy[i]! += uy * force;
        dx[j]! -= ux * force;
        dy[j]! -= uy * force;
      }
    }

    // Attraction along edges.
    for (const [a, b] of edges) {
      const ia = index.get(a);
      const ib = index.get(b);
      if (ia == null || ib == null) continue;
      const ddx = xs[ia]! - xs[ib]!;
      const ddy = ys[ia]! - ys[ib]!;
      const dist = Math.hypot(ddx, ddy) || 0.01;
      const force = (dist * dist) / k;
      const ux = ddx / dist;
      const uy = ddy / dist;
      dx[ia]! -= ux * force;
      dy[ia]! -= uy * force;
      dx[ib]! += ux * force;
      dy[ib]! += uy * force;
    }

    // Move each node, capped by the cooling temperature.
    for (let i = 0; i < n; i++) {
      const d = Math.hypot(dx[i]!, dy[i]!) || 0.01;
      const limited = Math.min(d, temp);
      xs[i]! += (dx[i]! / d) * limited;
      ys[i]! += (dy[i]! / d) * limited;
    }

    temp = Math.max(temp - cool, 0);
  }

  // Centre the layout on the origin.
  let cx = 0;
  let cy = 0;
  for (let i = 0; i < n; i++) {
    cx += xs[i]!;
    cy += ys[i]!;
  }
  cx /= n;
  cy /= n;
  for (let i = 0; i < n; i++) {
    positions.set(ids[i]!, { x: xs[i]! - cx, y: ys[i]! - cy });
  }
  return positions;
}
