import type {
  ExportClassConflict,
  ExportRoomConflict,
  ExportTeacherConflict,
} from "@/types/exporter";
import { ROUTES } from "@/routes";
import { withConflictParams } from "@/utils/exporter/formatters";
import { buildPath } from "@/utils/routes";

export function buildRoomConflictHref(projectId: string, row: ExportRoomConflict): string {
  return withConflictParams(
    buildPath(ROUTES.ROOM_DETAIL, {
      projectId,
      roomId: row.room_id,
    }),
    row,
  );
}

export function buildTeacherConflictHref(projectId: string, row: ExportTeacherConflict): string {
  return withConflictParams(
    buildPath(ROUTES.TEACHER_DETAIL, {
      projectId,
      teacherId: row.teacher_id,
    }),
    row,
  );
}

export function buildClassConflictHref(projectId: string, row: ExportClassConflict): string {
  return withConflictParams(
    buildPath(ROUTES.CLASS_DETAIL, {
      projectId,
      classId: row.class_id,
    }),
    row,
  );
}
