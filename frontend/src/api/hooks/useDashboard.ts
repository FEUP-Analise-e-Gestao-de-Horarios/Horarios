import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ApiResponse } from "@/types/api";
import type { ProjectExportPayload } from "@/types/exporter";

export { useProject } from "./project/project";

export function useProjectExport(projectId: string) {
  const recalculateExportGraph = useRef(false);
  const query = useQuery({
    queryKey: queryKeys.projects.export(projectId),
    queryFn: async (): Promise<ProjectExportPayload> => {
      const shouldRecalculate = recalculateExportGraph.current;
      recalculateExportGraph.current = false;
      const response = await api.post<ApiResponse<ProjectExportPayload>>(
        `/api/projects/${projectId}/export`,
        { recalculate_export_graph: shouldRecalculate },
      );
      return response.data;
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
