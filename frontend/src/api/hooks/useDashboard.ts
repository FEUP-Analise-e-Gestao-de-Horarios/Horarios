import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Project } from "@/types/project";
import type {
  DegreesApiResponse,
  DegreeStats,
  ProjectStats,
  RoomsApiResponse,
  RoomStats,
  StatsApiResponse,
  TeachersApiResponse,
  TeacherStats,
} from "@/types/dashboard";

const POLL_INTERVAL = 2000;

interface ProjectDetailResponse {
  data: Project;
}

function isProcessing(project: Project): boolean {
  return (
    !!project.ingestion_started_at && !project.ingestion_finished_at && !project.ingestion_failed_at
  );
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.detail(projectId),
    queryFn: async (): Promise<Project> => {
      const res = await api.get<ProjectDetailResponse>(`/api/projects/${projectId}`);
      return res.data;
    },
    enabled: !!projectId,
    refetchInterval: (query) =>
      query.state.data && !isProcessing(query.state.data) ? false : POLL_INTERVAL,
  });
}

export function useProjectStats(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.stats(projectId),
    queryFn: async (): Promise<ProjectStats> => {
      const res = await api.get<StatsApiResponse>(`/api/projects/${projectId}/stats`);
      return res.data;
    },
    enabled: !!projectId,
    refetchInterval,
  });
}

export function useProjectDegrees(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.degrees(projectId),
    queryFn: async (): Promise<DegreeStats[]> => {
      const res = await api.get<DegreesApiResponse>(`/api/projects/${projectId}/degrees/`);
      return res.data.degrees;
    },
    enabled: !!projectId,
    refetchInterval,
  });
}

export function useProjectTeachers(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.teachers(projectId),
    queryFn: async (): Promise<TeacherStats[]> => {
      const res = await api.get<TeachersApiResponse>(`/api/projects/${projectId}/teachers/`);
      return res.data.teachers;
    },
    enabled: !!projectId,
    refetchInterval,
  });
}

export function useProjectRooms(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.rooms(projectId),
    queryFn: async (): Promise<RoomStats[]> => {
      const res = await api.get<RoomsApiResponse>(`/api/projects/${projectId}/rooms/`);
      return res.data.rooms;
    },
    enabled: !!projectId,
    refetchInterval,
  });
}
