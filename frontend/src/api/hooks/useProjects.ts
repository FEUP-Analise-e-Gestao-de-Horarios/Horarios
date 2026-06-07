import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { ApiError } from "@/types/api";
import type { Project, ProjectsListPayload } from "@/types/project/project";
import type { ApiRequestError } from "@/types/api";

async function fetchProjects(): Promise<Project[]> {
  const payload = await api.getData<ProjectsListPayload>("/api/projects/");
  return payload.projects;
}

function hasProcessingProject(projects: Project[]): boolean {
  return projects.some(
    (p) => !!p.ingestion_started_at && !p.ingestion_finished_at && !p.ingestion_failed_at,
  );
}

export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects.all,
    queryFn: fetchProjects,
    refetchInterval: (query) =>
      query.state.data && hasProcessingProject(query.state.data) ? 5000 : false,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation<
    void,
    ApiRequestError<
      | typeof ApiError.AUTH_NOT_AUTHENTICATED
      | typeof ApiError.INVALID_BODY
      | typeof ApiError.PROJECTS_CREATE_DUPLICATED_NAME
      | typeof ApiError.PROJECTS_CREATE_FAILED
    >,
    { name: string; url: string }
  >({
    mutationFn: (data) => api.post<void>("/api/projects/", data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    },
  });
}

export function useRenameProject() {
  const queryClient = useQueryClient();
  return useMutation<
    void,
    ApiRequestError<
      | typeof ApiError.AUTH_NOT_AUTHENTICATED
      | typeof ApiError.INVALID_BODY
      | typeof ApiError.PROJECTS_NOT_FOUND
      | typeof ApiError.PROJECTS_RENAME_DUPLICATED_NAME
    >,
    { id: number; name: string }
  >({
    mutationFn: (params) => api.patch<void>(`/api/projects/${params.id}`, { name: params.name }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation<
    void,
    ApiRequestError<typeof ApiError.AUTH_NOT_AUTHENTICATED | typeof ApiError.PROJECTS_NOT_FOUND>,
    number
  >({
    mutationFn: (id) => api.delete<void>(`/api/projects/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    },
  });
}
