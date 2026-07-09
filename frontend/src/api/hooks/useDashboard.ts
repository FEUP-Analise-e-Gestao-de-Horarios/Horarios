import { useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

interface ExportChecklistResponse {
  checked_item_keys: string[];
}

export function useSetExportChecklistItem(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ itemKey, checked }: { itemKey: string; checked: boolean }) => {
      const response = await api.patch<ApiResponse<ExportChecklistResponse>>(
        `/api/projects/${projectId}/export/checklist`,
        { item_key: itemKey, checked },
      );
      return response.data;
    },
    onMutate: async ({ itemKey, checked }) => {
      const queryKey = queryKeys.projects.export(projectId);
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<ProjectExportPayload>(queryKey);
      queryClient.setQueryData<ProjectExportPayload>(queryKey, (current) => {
        if (!current) return current;
        const checkedItemKeys = new Set(current.checked_item_keys ?? []);
        if (checked) checkedItemKeys.add(itemKey);
        else checkedItemKeys.delete(itemKey);
        return { ...current, checked_item_keys: [...checkedItemKeys] };
      });
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.projects.export(projectId), context.previous);
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData<ProjectExportPayload>(
        queryKeys.projects.export(projectId),
        (current) =>
          current ? { ...current, checked_item_keys: data.checked_item_keys } : current,
      );
    },
  });
}

export function useClearExportChecklist(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await api.delete<ApiResponse<ExportChecklistResponse>>(
        `/api/projects/${projectId}/export/checklist`,
      );
      return response.data;
    },
    onMutate: async () => {
      const queryKey = queryKeys.projects.export(projectId);
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<ProjectExportPayload>(queryKey);
      queryClient.setQueryData<ProjectExportPayload>(queryKey, (current) =>
        current ? { ...current, checked_item_keys: [] } : current,
      );
      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.projects.export(projectId), context.previous);
      }
    },
    onSuccess: (data) => {
      queryClient.setQueryData<ProjectExportPayload>(
        queryKeys.projects.export(projectId),
        (current) =>
          current ? { ...current, checked_item_keys: data.checked_item_keys } : current,
      );
    },
  });
}
