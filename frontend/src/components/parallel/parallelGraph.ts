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
 * Deterministic layout for a component's nodes. One node is centred; two sit
 * side by side; three or more are spread evenly around a circle whose radius
 * grows with the node count.
 */
export function layoutNodes(ids: UUID[], radius: number): Map<UUID, NodePosition> {
  const positions = new Map<UUID, NodePosition>();
  const n = ids.length;
  if (n === 1) {
    positions.set(ids[0]!, { x: 0, y: 0 });
    return positions;
  }
  if (n === 2) {
    positions.set(ids[0]!, { x: -radius, y: 0 });
    positions.set(ids[1]!, { x: radius, y: 0 });
    return positions;
  }
  const start = -Math.PI / 2;
  for (let i = 0; i < n; i++) {
    const angle = start + (i * 2 * Math.PI) / n;
    positions.set(ids[i]!, {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    });
  }
  return positions;
}
