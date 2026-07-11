import { useMemo, useState } from "react";
import { buildAdjacency, isConnectedSelection } from "@/components/parallel/parallelGraphUtils";
import type { ParallelCandidateGraph, UUID } from "@/types/parallelSessions";

/** Owns the per-component in-progress node selection and the single source of
 * truth for whether a selection (or a group-all set) forms a valid group:
 * ≥2 nodes that are connected in the component's adjacency graph. Toggling is
 * blocked on nodes already assigned to a saved/draft group. */
export function useParallelSelection(
  graphs: ParallelCandidateGraph[],
  assignedBlockIds: Set<UUID>,
) {
  const [selectionByGroup, setSelectionByGroup] = useState<Record<UUID, Set<UUID>>>({});

  const adjacencyByGroup = useMemo(() => {
    const map = new Map<UUID, Map<UUID, Set<UUID>>>();
    for (const g of graphs) map.set(g.candidate_group_id, buildAdjacency(g.edges));
    return map;
  }, [graphs]);

  // A selected set is a valid group when it holds ≥2 nodes that stay connected
  // in the component's adjacency graph.
  const isConnectedGroup = (candidateGroupId: UUID, blockIds: Set<UUID>): boolean => {
    if (blockIds.size < 2) return false;
    const adj = adjacencyByGroup.get(candidateGroupId);
    if (!adj) return false;
    return isConnectedSelection(blockIds, adj);
  };

  /** Whether the current selection for a component is a valid (connected, ≥2) group. */
  const isSelectionValid = (candidateGroupId: UUID): boolean =>
    isConnectedGroup(candidateGroupId, selectionByGroup[candidateGroupId] ?? new Set());

  // Block ids of a component still free to be grouped (not already assigned).
  const unassignedBlockIds = (candidateGroupId: UUID): UUID[] => {
    const graph = graphs.find((g) => g.candidate_group_id === candidateGroupId);
    if (!graph) return [];
    return graph.nodes.map((n) => n.original_block_id).filter((id) => !assignedBlockIds.has(id));
  };

  /** Whether all still-unassigned nodes of a component form a valid group. */
  const canGroupAll = (candidateGroupId: UUID): boolean =>
    isConnectedGroup(candidateGroupId, new Set(unassignedBlockIds(candidateGroupId)));

  /** The current selection for a component as a block-id array (for group create). */
  const selectionBlockIds = (candidateGroupId: UUID): UUID[] => [
    ...(selectionByGroup[candidateGroupId] ?? []),
  ];

  const handleToggleNode = (candidateGroupId: UUID, blockId: UUID) => {
    if (assignedBlockIds.has(blockId)) return;
    setSelectionByGroup((prev) => {
      const current = new Set(prev[candidateGroupId] ?? []);
      if (current.has(blockId)) current.delete(blockId);
      else current.add(blockId);
      return { ...prev, [candidateGroupId]: current };
    });
  };

  /** Clear every component's in-progress selection (e.g. on degree change). */
  const clearSelection = () => setSelectionByGroup({});

  /** Clear a single component's selection (e.g. once its group is created). */
  const clearSelectionFor = (candidateGroupId: UUID) =>
    setSelectionByGroup((prev) => ({ ...prev, [candidateGroupId]: new Set() }));

  return {
    selectionByGroup,
    isSelectionValid,
    canGroupAll,
    unassignedBlockIds,
    selectionBlockIds,
    handleToggleNode,
    clearSelection,
    clearSelectionFor,
  };
}
