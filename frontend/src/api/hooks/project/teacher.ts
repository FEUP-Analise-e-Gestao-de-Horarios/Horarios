import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { TeacherDetail, TeachersListPayload, TeacherStats } from "@/types/dashboard";

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

export function useProjectTeacher(projectId: string, teacherId: string) {
  return useQuery({
    queryKey: queryKeys.projects.teacher(projectId, teacherId),
    queryFn: () => api.getData<TeacherDetail>(`/api/projects/${projectId}/teachers/${teacherId}`),
    enabled: !!projectId && !!teacherId,
  });
}
