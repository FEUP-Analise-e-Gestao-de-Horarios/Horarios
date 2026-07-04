import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ParallelCandidateGraph, SuccessResponse } from "@/types/parallelSessions";
import { getErrorMessage } from "./errors";

/** Fetches the parallel candidate graphs for a project and exposes the raw
 * payload (which the confirm/group state seeds from) alongside a memoised
 * `graphs` array and the loading/error flags every consumer reads. */
export function useParallelCandidatesQuery(projectIdNum: number, enabled: boolean) {
  const candidatesQuery = useQuery({
    queryKey: queryKeys.projects.parallelCandidates(String(projectIdNum)),
    queryFn: async () => {
      const res = await api.get<SuccessResponse<ParallelCandidateGraph[]>>(
        `/api/projects/${projectIdNum}/parallel-blocks/candidates`,
      );
      return res.data;
    },
    enabled,
    // The graph structure is stable for a session; groups are mutated locally
    // and persisted separately, so never auto-refetch this payload.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const graphs = useMemo(() => candidatesQuery.data ?? [], [candidatesQuery.data]);
  const loadingCandidates = candidatesQuery.isLoading;
  const candidatesError = candidatesQuery.error
    ? getErrorMessage(candidatesQuery.error, "Failed to load parallel candidates")
    : null;

  return {
    /** The raw payload the confirm/group seeding effects derive their state from. */
    candidatesData: candidatesQuery.data,
    graphs,
    loadingCandidates,
    candidatesError,
  };
}
