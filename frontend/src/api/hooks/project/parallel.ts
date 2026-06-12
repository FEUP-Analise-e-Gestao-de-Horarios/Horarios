import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { mockParallelBlocks } from "@/api/mocks/scheduleMocks";
import { queryKeys } from "@/api/queryKeys";
import { FLAGS } from "@/config/featureFlags";
import type { ParallelBlocksPayload } from "@/types/project/parallel";

/**
 * Slots blocked for a session by its parallel classes (contract C4). Mock
 * returns no restrictions, so the unavailability overlay works without it.
 */
export function useParallelBlocks(projectId: string, sessionId: string) {
  return useQuery({
    queryKey: queryKeys.projects.parallelBlocks(projectId, sessionId),
    queryFn: () =>
      FLAGS.parallelBlocks
        ? api.getData<ParallelBlocksPayload>(
            `/api/projects/${projectId}/parallel-blocks/?session_id=${sessionId}`,
          )
        : mockParallelBlocks(),
    enabled: !!projectId && !!sessionId,
  });
}
