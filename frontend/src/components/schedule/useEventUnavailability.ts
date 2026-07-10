import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { RoomDetail } from "@/types/project/room";
import type { TeacherDetail } from "@/types/project/teacher";
import type { WeekGridEvent, WeekGridMark } from "./WeekGrid";

const STALE_TIME_MS = 5 * 60 * 1000;

/**
 * Red blocks of the selected event's teacher(s) and room(s), deduplicated into
 * grid marks (PI ToDo #5): each unavailable slot yields one `kind: "unavailable"`
 * mark, whether it's blocked by a teacher, the room, or both. Fetches the same
 * detail endpoints the hover tooltips use, so they're already cached.
 */
export function useEventUnavailability(
  projectId: string,
  event: WeekGridEvent | null | undefined,
): WeekGridMark[] {
  const teacherIds = event?.teachers?.map((teacher) => teacher.id) ?? [];
  const roomIds = event?.rooms?.map((room) => room.id) ?? [];

  const teacherQueries = useQueries({
    queries: teacherIds.map((id) => ({
      queryKey: queryKeys.projects.teacher(projectId, id),
      queryFn: () => api.getData<TeacherDetail>(`/api/projects/${projectId}/teachers/${id}`),
      enabled: !!projectId && !!id,
      staleTime: STALE_TIME_MS,
    })),
  });

  const roomQueries = useQueries({
    queries: roomIds.map((id) => ({
      queryKey: queryKeys.projects.room(projectId, id),
      queryFn: () => api.getData<RoomDetail>(`/api/projects/${projectId}/rooms/${id}`),
      enabled: !!projectId && !!id,
      staleTime: STALE_TIME_MS,
    })),
  });

  const teacherData = teacherQueries.map((query) => query.data);
  const roomData = roomQueries.map((query) => query.data);
  // Stable signatures so the memo recomputes only when the red blocks change.
  const teacherSignature = JSON.stringify(teacherData.map((data) => data?.red_blocks));
  const roomSignature = JSON.stringify(roomData.map((data) => data?.red_blocks));

  return useMemo(() => {
    const blocked = new Map<string, { weekday: string; hour: number }>();
    const add = (blocks: { weekday: string; hour: number }[] | undefined) => {
      for (const block of blocks ?? []) {
        blocked.set(`${block.weekday}-${block.hour}`, { weekday: block.weekday, hour: block.hour });
      }
    };
    teacherData.forEach((data) => add(data?.red_blocks));
    roomData.forEach((data) => add(data?.red_blocks));

    return [...blocked.entries()].map(([key, entry]) => ({
      id: `unavail-${key}`,
      weekday: entry.weekday as WeekGridMark["weekday"],
      time: entry.hour,
      kind: "unavailable" as const,
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [teacherSignature, roomSignature]);
}
