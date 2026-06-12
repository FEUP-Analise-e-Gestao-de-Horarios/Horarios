import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { mockPermissions } from "@/api/mocks/scheduleMocks";
import { queryKeys } from "@/api/queryKeys";
import { FLAGS } from "@/config/featureFlags";
import type { PermissionsPayload } from "@/types/project/permissions";

/** Degrees the current user may edit (contract C5). Mock: admin-by-default. */
export function useProjectPermissions(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.permissions(projectId),
    queryFn: () =>
      FLAGS.permissionsApi
        ? api.getData<PermissionsPayload>(`/api/projects/${projectId}/permissions/`)
        : mockPermissions(),
    enabled: !!projectId,
  });
}
