import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { FLAGS } from "@/config/featureFlags";
import type { ApiResponse } from "@/types/api";
import type { SessionPatch, SessionResponse } from "@/types/project/sessions";

/**
 * Move/edit a session (contract C1). While `FLAGS.sessionMutations` is off the
 * mutation resolves with null and persists nothing — unsaved changes live in
 * the local-edit layer (`useLocalSessionEdits`) instead, so callers share one
 * code path before and after the endpoint ships.
 */
export function useUpdateSession(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      sessionId,
      patch,
    }: {
      sessionId: string;
      patch: SessionPatch;
    }): Promise<SessionResponse | null> => {
      if (!FLAGS.sessionMutations) return null;
      const res = await api.patch<ApiResponse<SessionResponse>>(
        `/api/projects/${projectId}/sessions/${sessionId}/`,
        patch,
      );
      return res.data;
    },
    onSuccess: (updated) => {
      if (!updated) return;
      void queryClient.invalidateQueries({
        queryKey: queryKeys.projects.sessionsRoot(projectId),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.projects.conflictsRoot(projectId),
      });
    },
  });
}
