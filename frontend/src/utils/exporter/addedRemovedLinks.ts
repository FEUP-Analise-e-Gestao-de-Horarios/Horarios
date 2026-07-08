import type { ExportSessionRecord } from "@/types/exporter";
import type { Weekday } from "@/types/project/weekday";
import { ROUTES } from "@/routes";
import { subjectTitleLabel, uniqueByLabel } from "@/utils/exporter/relations";
import { buildPath } from "@/utils/routes";

export type AddedRemovedSessionChange = "added" | "removed";

function sessionTitle(session: ExportSessionRecord): string {
  const classes = uniqueByLabel(session.classes ?? [], (classCode) => classCode).join(", ");
  const subjects = uniqueByLabel(session.subjects ?? [], subjectTitleLabel)
    .map((subject) =>
      [subject.acronym ?? subject.name, subject.code ? `(${subject.code})` : ""]
        .filter(Boolean)
        .join(" "),
    )
    .join(", ");

  return [classes, subjects].filter(Boolean).join(" · ") || "Aula";
}

function sessionBody(session: ExportSessionRecord): string[] {
  return [
    session.teachers?.map((teacher) => teacher.acronym || teacher.name).join(", "),
    session.rooms?.join(", "),
  ].filter((line): line is string => !!line);
}

function targetPath(projectId: string): string {
  return buildPath(ROUTES.EXPORT_SESSION_CONTEXT, { projectId });
}

function normalizeWeekday(value: string | null | undefined): Weekday | null {
  const normalized = value?.toLowerCase();
  if (
    normalized === "monday" ||
    normalized === "tuesday" ||
    normalized === "wednesday" ||
    normalized === "thursday" ||
    normalized === "friday" ||
    normalized === "saturday"
  ) {
    return normalized;
  }
  return null;
}

export function buildAddedRemovedSessionHref(
  projectId: string,
  session: ExportSessionRecord,
  change: AddedRemovedSessionChange,
): string | null {
  const weekday = normalizeWeekday(session.weekday);
  if (!projectId || !session.week || !weekday) return null;
  if (typeof session.start_time !== "number" || typeof session.duration !== "number") return null;

  const path = targetPath(projectId);

  const params = new URLSearchParams({
    week: session.week,
    exportSession: session.id,
    exportSessionChange: change,
    exportSessionWeek: session.week,
    exportSessionWeekday: weekday,
    exportSessionStart: String(session.start_time),
    exportSessionDuration: String(session.duration),
    exportSessionTitle: sessionTitle(session),
  });
  if (session.type) params.set("exportSessionType", session.type);
  if (session.class_ids?.length) params.set("exportSessionClassIds", session.class_ids.join(","));
  if (session.room_ids?.length) params.set("exportSessionRoomIds", session.room_ids.join(","));
  if (session.teacher_ids?.length) {
    params.set("exportSessionTeacherIds", session.teacher_ids.join(","));
  }

  const body = sessionBody(session);
  if (body.length) params.set("exportSessionBody", JSON.stringify(body));

  return `${path}?${params.toString()}`;
}
