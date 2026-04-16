import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ApiResponse } from "@/types/api";
import type { Project } from "@/types/project";
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
} from "@/types/dashboard";

const POLL_INTERVAL = 2000;

function isProcessing(project: Project): boolean {
  return (
    !!project.ingestion_started_at && !project.ingestion_finished_at && !project.ingestion_failed_at
  );
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.detail(projectId),
    queryFn: async (): Promise<Project> => {
      const res = await api.get<ApiResponse<Project>>(`/api/projects/${projectId}`);
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
      const res = await api.get<ApiResponse<ProjectStats>>(`/api/projects/${projectId}/stats`);
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
      const res = await api.get<ApiResponse<DegreesListPayload>>(
        `/api/projects/${projectId}/degrees/`,
      );
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
      const res = await api.get<ApiResponse<TeachersListPayload>>(
        `/api/projects/${projectId}/teachers/`,
      );
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
      const res = await api.get<ApiResponse<RoomsListPayload>>(`/api/projects/${projectId}/rooms/`);
      return res.data.rooms;
    },
    enabled: !!projectId,
    refetchInterval,
  });
}

export function useProjectDegree(projectId: string, degreeId: string) {
  return useQuery({
    queryKey: queryKeys.projects.degree(projectId, degreeId),
    queryFn: async (): Promise<DegreeDetail> => {
      const res = await api.get<ApiResponse<DegreeDetail>>(
        `/api/projects/${projectId}/degrees/${degreeId}`,
      );
      return res.data;
    },
    enabled: !!projectId && !!degreeId,
  });
}

export function useProjectTeacher(projectId: string, teacherId: string) {
  return useQuery({
    queryKey: queryKeys.projects.teacher(projectId, teacherId),
    queryFn: async (): Promise<TeacherDetail> => {
      const res = await api.get<ApiResponse<TeacherDetail>>(
        `/api/projects/${projectId}/teachers/${teacherId}`,
      );
      return res.data;
    },
    enabled: !!projectId && !!teacherId,
  });
}

export function useProjectRoom(projectId: string, roomId: string) {
  return useQuery({
    queryKey: queryKeys.projects.room(projectId, roomId),
    queryFn: async (): Promise<RoomDetail> => {
      const res = await api.get<ApiResponse<RoomDetail>>(
        `/api/projects/${projectId}/rooms/${roomId}`,
      );
      return res.data;
    },
    enabled: !!projectId && !!roomId,
  });
}

export function useProjectSubject(projectId: string, subjectId: string) {
  return useQuery({
    queryKey: queryKeys.projects.subject(projectId, subjectId),
    queryFn: async (): Promise<SubjectDetail> => {
      const res = await api.get<ApiResponse<SubjectDetail>>(
        `/api/projects/${projectId}/subjects/${subjectId}`,
      );
      return res.data;
    },
    enabled: !!projectId && !!subjectId,
  });
}

export function useProjectClass(projectId: string, classId: string) {
  return useQuery({
    queryKey: queryKeys.projects.class(projectId, classId),
    queryFn: async (): Promise<ClassDetail> => {
      const res = await api.get<ApiResponse<ClassDetail>>(
        `/api/projects/${projectId}/classes/${classId}`,
      );
      return res.data;
    },
    enabled: !!projectId && !!classId,
  });
}
