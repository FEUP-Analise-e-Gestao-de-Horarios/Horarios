import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type {
  ConflictPreviewRequest,
  ConflictPreviewResponse,
  ConflictRecord,
  ConflictsListPayload,
} from "@/types/project/conflicts";
import type { ApiResponse } from "@/types/api";
import type { YearDetail } from "@/types/project/year";

const conflictsKey = (projectId: string) => ["projects", projectId, "conflicts"] as const;

export function useProjectYear(projectId: string, yearId: string) {
  return useQuery({
    queryKey: queryKeys.projects.year(projectId, yearId),
    queryFn: () => api.getData<YearDetail>(`/api/projects/${projectId}/years/${yearId}`),
    enabled: !!projectId && !!yearId,
  });
}

export function useProjectConflicts(projectId: string) {
  return useQuery({
    queryKey: conflictsKey(projectId),
    queryFn: () =>
      api
        .getData<ConflictsListPayload>(`/api/projects/${projectId}/conflicts`)
        .then((d) => d.conflicts),
    enabled: !!projectId,
    initialData: [] as ConflictRecord[],
  });
}

export function usePreviewConflicts(projectId: string) {
  return useMutation({
    mutationFn: (body: ConflictPreviewRequest) =>
      api
        .post<
          ApiResponse<ConflictPreviewResponse>
        >(`/api/projects/${projectId}/conflicts/preview`, body)
        .then((r) => r.data),
  });
}

export function useUpdateConflictTag(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conflictId, tag }: { conflictId: string; tag: string | null }) =>
      api.patch<void>(`/api/projects/${projectId}/conflicts/${conflictId}`, { tag }),
    onMutate: async ({ conflictId, tag }) => {
      await queryClient.cancelQueries({ queryKey: conflictsKey(projectId) });
      const previous = queryClient.getQueryData<ConflictRecord[]>(conflictsKey(projectId));
      queryClient.setQueryData<ConflictRecord[]>(conflictsKey(projectId), (old) =>
        (old ?? []).map((c) => (c.id === conflictId ? { ...c, tag } : c)),
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(conflictsKey(projectId), context.previous);
      }
    },
  });
}
