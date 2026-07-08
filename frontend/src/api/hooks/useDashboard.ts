import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ApiResponse } from "@/types/api";
import type { ProjectExportApiPayload, ProjectExportPayload } from "@/types/exporter";
import { compactExportToProjectExportPayload } from "@/utils/exporter/exportCompact";

export { useProject } from "./project/project";

function hasAddedRemovedNavigationData(data: ProjectExportPayload): boolean {
  return [...data.added_removed_sessions.added, ...data.added_removed_sessions.removed].every(
    (session) =>
      !!session.week &&
      !!session.weekday &&
      typeof session.start_time === "number" &&
      typeof session.duration === "number" &&
      Boolean(session.class_ids?.length || session.room_ids?.length || session.teacher_ids?.length),
  );
}

export function useProjectExport(projectId: string) {
  const recalculateExportGraph = useRef(false);
  const refreshedAddedRemovedNavigation = useRef(false);
  const query = useQuery({
    queryKey: queryKeys.projects.export(projectId),
    queryFn: async (): Promise<ProjectExportPayload> => {
      const shouldRecalculate = recalculateExportGraph.current;
      recalculateExportGraph.current = false;
      const response = await api.post<ApiResponse<ProjectExportApiPayload>>(
        `/api/projects/${projectId}/export`,
        { recalculate_export_graph: shouldRecalculate, payload_format: "compact" },
      );
      const data = compactExportToProjectExportPayload(response.data);

      if (
        !shouldRecalculate &&
        !refreshedAddedRemovedNavigation.current &&
        !hasAddedRemovedNavigationData(data)
      ) {
        refreshedAddedRemovedNavigation.current = true;
        const refreshed = await api.post<ApiResponse<ProjectExportApiPayload>>(
          `/api/projects/${projectId}/export`,
          { recalculate_export_graph: true, payload_format: "compact" },
        );
        return compactExportToProjectExportPayload(refreshed.data);
      }

      return data;
    },
    enabled: !!projectId,
    refetchOnWindowFocus: false,
    staleTime: 0,
  });

  return {
    ...query,
    recalculateExportGraph: () => {
      recalculateExportGraph.current = true;
      return query.refetch();
    },
  };
}
