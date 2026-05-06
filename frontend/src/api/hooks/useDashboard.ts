import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys, type SessionsQueryFilters } from "@/api/queryKeys";
import type { Project } from "@/types/project";
import type {
  ClassDetail,
  ConflictRecord,
  DegreeDetail,
  DegreesListPayload,
  DegreeStats,
  ProjectStats,
  RoomDetail,
  RoomsListPayload,
  RoomStats,
  SessionsResponse,
  SubjectDetail,
  TeacherDetail,
  TeachersListPayload,
  TeacherStats,
  WeekBlockResponse,
  YearDetail,
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

export function useProjectSessions(projectId: string, filters: SessionsQueryFilters) {
  return useQuery({
    queryKey: queryKeys.projects.sessions(projectId, filters),
    queryFn: async (): Promise<WeekBlockResponse[]> => {
      const params = new URLSearchParams();
      params.set("year_id", filters.yearId);
      for (const id of filters.subjectIds) params.append("subject_ids", id);
      for (const id of filters.classIds) params.append("class_ids", id);
      for (const day of filters.weekdays) params.append("weekdays", day);
      const payload = await api.getData<SessionsResponse>(
        `/api/projects/${projectId}/sessions/?${params.toString()}`,
      );
      return payload.blocks;
    },
    enabled: !!projectId && !!filters.yearId,
  });
}

export function useProjectYearConflicts(projectId: string, yearId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "years", yearId, "conflicts"] as const,
    queryFn: (): ConflictRecord[] => [],
    enabled: false,
    initialData: [] as ConflictRecord[],
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
