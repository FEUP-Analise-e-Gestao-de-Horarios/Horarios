import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type {
  ConflictPreviewRequest,
  ConflictPreviewResponse,
  ConflictRecord,
  ConflictsListPayload,
  UpdateManyConflictTagsRequest,
  UpdateManyConflictTagsResponse,
} from "@/types/project/conflicts";
import type { ApiResponse } from "@/types/api";
import type { YearDetail } from "@/types/project/year";

const conflictsKey = (projectId: string) => ["projects", projectId, "conflicts"] as const;
const tagsKey = (projectId: string) => ["projects", projectId, "conflicts", "tags"] as const;

export function useProjectYear(projectId: string, yearId: string) {
  return useQuery({
    queryKey: queryKeys.projects.year(projectId, yearId),
    queryFn: () => api.getData<YearDetail>(`/api/projects/${projectId}/years/${yearId}`),
    enabled: !!projectId && !!yearId,
  });
}

export function useProjectConflicts(projectId: string, enabled = false) {
  return useQuery({
    queryKey: conflictsKey(projectId),
    queryFn: () =>
      api
        .getData<ConflictsListPayload>(`/api/projects/${projectId}/conflicts`)
        .then((d) => d.conflicts),
    enabled: !!projectId && enabled,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    placeholderData: [] as ConflictRecord[],
  });
}

export function useProjectConflictTags(projectId: string, enabled = false) {
  return useQuery({
    queryKey: tagsKey(projectId),
    queryFn: () =>
      api
        .getData<{ tags: string[] }>(`/api/projects/${projectId}/conflicts/tags`)
        .then((d) => d.tags),
    enabled: !!projectId && enabled,
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    placeholderData: [] as string[],
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

export function useUpdateConflictTags(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ conflictId, tags }: { conflictId: string; tags: string[] }) =>
      api.patch<void>(`/api/projects/${projectId}/conflicts/${conflictId}`, { tags }),
    onMutate: async ({ conflictId, tags }) => {
      await queryClient.cancelQueries({ queryKey: conflictsKey(projectId) });
      const previous = queryClient.getQueryData<ConflictRecord[]>(conflictsKey(projectId));
      queryClient.setQueryData<ConflictRecord[]>(conflictsKey(projectId), (old) =>
        (old ?? []).map((c) => (c.id === conflictId ? { ...c, tags } : c)),
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(conflictsKey(projectId), context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: tagsKey(projectId) });
    },
  });
}

export function useUpdateManyConflictTags(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (updates: UpdateManyConflictTagsRequest["updates"]) =>
      api
        .patch<
          ApiResponse<UpdateManyConflictTagsResponse>
        >(`/api/projects/${projectId}/conflicts`, { updates })
        .then((r) => r.data),
    onMutate: async (updates) => {
      await queryClient.cancelQueries({ queryKey: conflictsKey(projectId) });
      const previous = queryClient.getQueryData<ConflictRecord[]>(conflictsKey(projectId));
      const tagsById = new Map(updates.map((u) => [u.conflict_id, u.tags]));
      queryClient.setQueryData<ConflictRecord[]>(conflictsKey(projectId), (old) =>
        (old ?? []).map((c) => (tagsById.has(c.id) ? { ...c, tags: tagsById.get(c.id)! } : c)),
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(conflictsKey(projectId), context.previous);
      }
    },
    onSuccess: ({ conflicts }) => {
      const byId = new Map(conflicts.map((c) => [c.id, c]));
      queryClient.setQueryData<ConflictRecord[]>(conflictsKey(projectId), (old) =>
        (old ?? []).map((c) => byId.get(c.id) ?? c),
      );
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: tagsKey(projectId) });
    },
  });
}

export function useDeleteConflictTag(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagName: string) =>
      api.delete<void>(`/api/projects/${projectId}/conflicts/tags/${encodeURIComponent(tagName)}`),
    onMutate: async (tagName) => {
      await queryClient.cancelQueries({ queryKey: conflictsKey(projectId) });
      const previous = queryClient.getQueryData<ConflictRecord[]>(conflictsKey(projectId));
      queryClient.setQueryData<ConflictRecord[]>(conflictsKey(projectId), (old) =>
        (old ?? []).map((c) =>
          c.tags.includes(tagName) ? { ...c, tags: c.tags.filter((t) => t !== tagName) } : c,
        ),
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(conflictsKey(projectId), context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: tagsKey(projectId) });
    },
  });
}
