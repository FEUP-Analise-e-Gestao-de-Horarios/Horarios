import type { ParallelCandidateEdge, UUID } from "@/types/parallelSessions";

/** Build an undirected adjacency map from an edge list. */
export function buildAdjacency(edges: ParallelCandidateEdge[]): Map<UUID, Set<UUID>> {
  const adj = new Map<UUID, Set<UUID>>();
  const link = (a: UUID, b: UUID) => {
    let set = adj.get(a);
    if (!set) {
      set = new Set();
      adj.set(a, set);
    }
    set.add(b);
  };
  for (const { source: a, target: b } of edges) {
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
