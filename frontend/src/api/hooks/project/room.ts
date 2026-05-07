import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { RoomDetail, RoomsListPayload, RoomStats } from "@/types/dashboard";

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

export function useProjectRoom(projectId: string, roomId: string) {
  return useQuery({
    queryKey: queryKeys.projects.room(projectId, roomId),
    queryFn: () => api.getData<RoomDetail>(`/api/projects/${projectId}/rooms/${roomId}`),
    enabled: !!projectId && !!roomId,
  });
}
