import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { mockConflicts, mockSetConflictIgnored } from "@/api/mocks/scheduleMocks";
import { queryKeys } from "@/api/queryKeys";
import { FLAGS } from "@/config/featureFlags";
import type { ApiResponse } from "@/types/api";
import type {
  ConflictIgnoredResult,
  ConflictScope,
  ConflictsListPayload,
} from "@/types/project/conflicts";

/**
 * Conflicts for a project, sliced by scope (contract C2). Mock-backed until
 * `FLAGS.conflictsApi` is on; `scope === "year"` additionally needs a yearId.
 */
export function useProjectConflicts(
  projectId: string,
  scope: ConflictScope,
  options: { yearId?: string; includeIgnored?: boolean } = {},
) {
  const { yearId = "", includeIgnored = false } = options;
  return useQuery({
    queryKey: queryKeys.projects.conflicts(projectId, scope, yearId, includeIgnored),
    queryFn: async () => {
      if (!FLAGS.conflictsApi) {
        return mockConflicts(scope, { yearId, includeIgnored }).conflicts;
      }
      const params = new URLSearchParams({ scope, include_ignored: String(includeIgnored) });
      if (yearId) params.set("year_id", yearId);
      const payload = await api.getData<ConflictsListPayload>(
        `/api/projects/${projectId}/conflicts/?${params}`,
      );
      return payload.conflicts;
    },
    enabled: !!projectId && (scope !== "year" || !!yearId),
  });
}

/** Ignore / restore a conflict (contract C3). */
export function useSetConflictIgnored(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      conflictId,
      ignored,
    }: {
      conflictId: string;
      ignored: boolean;
    }): Promise<ConflictIgnoredResult> => {
      if (!FLAGS.conflictsApi) return mockSetConflictIgnored(conflictId, ignored);
      const url = `/api/projects/${projectId}/conflicts/${conflictId}/ignore/`;
      const res = ignored
        ? await api.post<ApiResponse<ConflictIgnoredResult>>(url, {})
        : await api.delete<ApiResponse<ConflictIgnoredResult>>(url);
      return res.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.projects.conflictsRoot(projectId),
      });
    },
  });
}
