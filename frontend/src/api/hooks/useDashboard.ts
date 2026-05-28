import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Project } from "@/types/project";
import type { ApiResponse } from "@/types/api";
import type {
  ClassDetail,
  DegreeDetail,
  DegreesListPayload,
  DegreeStats,
  ProjectStats,
  RoomDetail,
  RoomsListPayload,
  RoomStats,
  SubjectDetail,
  TeacherDetail,
  TeachersListPayload,
  TeacherStats,
  YearDetail,
} from "@/types/dashboard";
import type { ProjectExportPayload } from "@/types/exporter";

const POLL_INTERVAL = 2000;

function isProcessing(project: Project): boolean {
  return (
    !!project.ingestion_started_at && !project.ingestion_finished_at && !project.ingestion_failed_at
  );
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.detail(projectId),
    queryFn: () => api.getData<Project>(`/api/projects/${projectId}`),
    enabled: !!projectId,
    refetchInterval: (query) =>
      query.state.data && !isProcessing(query.state.data) ? false : POLL_INTERVAL,
  });
}

export function useProjectStats(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.stats(projectId),
    queryFn: () => api.getData<ProjectStats>(`/api/projects/${projectId}/stats`),
    enabled: !!projectId,
    refetchInterval,
  });
}

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

export function useProjectDegrees(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.degrees(projectId),
    queryFn: async (): Promise<DegreeStats[]> => {
      const payload = await api.getData<DegreesListPayload>(`/api/projects/${projectId}/degrees/`);
      return payload.degrees;
    },
    enabled: !!projectId,
    refetchInterval,
  });
}

export function useProjectTeachers(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.teachers(projectId),
    queryFn: async (): Promise<TeacherStats[]> => {
      const payload = await api.getData<TeachersListPayload>(
        `/api/projects/${projectId}/teachers/`,
      );
      return payload.teachers;
    },
    enabled: !!projectId,
    refetchInterval,
  });
}

export function useProjectRooms(projectId: string, refetchInterval: number | false = false) {
  return useQuery({
    queryKey: queryKeys.projects.rooms(projectId),
    queryFn: async (): Promise<RoomStats[]> => {
      const payload = await api.getData<RoomsListPayload>(`/api/projects/${projectId}/rooms/`);
      return payload.rooms;
    },
    enabled: !!projectId,
    refetchInterval,
  });
}

export function useProjectDegree(projectId: string, degreeId: string) {
  return useQuery({
    queryKey: queryKeys.projects.degree(projectId, degreeId),
    queryFn: () => api.getData<DegreeDetail>(`/api/projects/${projectId}/degrees/${degreeId}`),
    enabled: !!projectId && !!degreeId,
  });
}

export function useProjectYear(projectId: string, yearId: string) {
  return useQuery({
    queryKey: queryKeys.projects.year(projectId, yearId),
    queryFn: () => api.getData<YearDetail>(`/api/projects/${projectId}/years/${yearId}`),
    enabled: !!projectId && !!yearId,
  });
}

export function useProjectTeacher(projectId: string, teacherId: string) {
  return useQuery({
    queryKey: queryKeys.projects.teacher(projectId, teacherId),
    queryFn: () => api.getData<TeacherDetail>(`/api/projects/${projectId}/teachers/${teacherId}`),
    enabled: !!projectId && !!teacherId,
  });
}

export function useProjectRoom(projectId: string, roomId: string) {
  return useQuery({
    queryKey: queryKeys.projects.room(projectId, roomId),
    queryFn: () => api.getData<RoomDetail>(`/api/projects/${projectId}/rooms/${roomId}`),
    enabled: !!projectId && !!roomId,
  });
}

export function useProjectSubject(projectId: string, subjectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.subject(projectId, subjectId),
    queryFn: () => api.getData<SubjectDetail>(`/api/projects/${projectId}/subjects/${subjectId}`),
    enabled: !!projectId && !!subjectId,
  });
}

export function useProjectClass(projectId: string, classId: string) {
  return useQuery({
    queryKey: queryKeys.projects.class(projectId, classId),
    queryFn: () => api.getData<ClassDetail>(`/api/projects/${projectId}/classes/${classId}`),
    enabled: !!projectId && !!classId,
  });
}
