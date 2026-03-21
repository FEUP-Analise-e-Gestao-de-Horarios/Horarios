import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Project, ProjectsResponse } from "@/types/project";
import type { ApiRequestError } from "@/types/api";

async function fetchProjects(): Promise<Project[]> {
  const res = await api.get<ProjectsResponse>("/api/projects/");
  return res.data.projects;
}

export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects.all,
    queryFn: fetchProjects,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiRequestError, { name: string; url: string }>({
    mutationFn: (data) => api.post<void>("/api/projects/", data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    },
  });
}

export function useRenameProject() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiRequestError, { id: string; name: string }>({
    mutationFn: (params) => api.patch<void>(`/api/projects/${params.id}/`, { name: params.name }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiRequestError, string>({
    mutationFn: (id) => api.delete<void>(`/api/projects/${id}/`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    },
  });
}
