import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { FLAGS } from "@/config/featureFlags";
import type { ApiResponse } from "@/types/api";
import type {
  SessionMerge,
  SessionPatch,
  SessionResponse,
  SessionSplit,
  SessionSplitResult,
} from "@/types/project/sessions";

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

/**
 * Detach some of a session's classes into a brand new session. Unlike the
 * placement/swap/Guardar mutations, a split has no local-edit preview —
 * the local-edit layer only overrides existing session ids, it can't add a
 * new one — so the grid only shows the result once this resolves and the
 * sessions query refetches.
 */
export function useSplitSession(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      sessionId,
      split,
    }: {
      sessionId: string;
      split: SessionSplit;
    }): Promise<SessionSplitResult | null> => {
      if (!FLAGS.sessionMutations) return null;
      const res = await api.post<ApiResponse<SessionSplitResult>>(
        `/api/projects/${projectId}/sessions/${sessionId}/split/`,
        split,
      );
      return res.data;
    },
    onSuccess: (result) => {
      if (!result) return;
      void queryClient.invalidateQueries({
        queryKey: queryKeys.projects.sessionsRoot(projectId),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.projects.conflictsRoot(projectId),
      });
    },
  });
}

/**
 * Recombine a session's classes into a matching sibling, deleting the
 * caller — the reverse of a split. No local-edit preview, same reason as a
 * split: the local-edit layer can't represent one session disappearing
 * into another, so the grid only shows the result once this resolves.
 */
export function useMergeSession(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      sessionId,
      merge,
    }: {
      sessionId: string;
      merge: SessionMerge;
    }): Promise<SessionResponse | null> => {
      if (!FLAGS.sessionMutations) return null;
      const res = await api.post<ApiResponse<SessionResponse>>(
        `/api/projects/${projectId}/sessions/${sessionId}/merge/`,
        merge,
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
