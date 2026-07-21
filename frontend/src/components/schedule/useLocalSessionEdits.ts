import { useState } from "react";
import type { ClassBase } from "@/types/project/class";
import type { RoomBase } from "@/types/project/room";
import type { SessionResponse, WeekBlockResponse } from "@/types/project/sessions";
import type { SubjectBase } from "@/types/project/subject";
import type { TeacherBase } from "@/types/project/teacher";
import { timeToHhmm } from "@/utils/time";
import type { EventDrawerFormState } from "./useEventDrawerForm";

/** An in-memory edit applied to one session, keyed by session id. Never persisted. */
export type SessionOverride = Partial<
  Pick<
    SessionResponse,
    "weekday" | "start_time" | "duration" | "subjects" | "teachers" | "rooms" | "classes"
  >
>;

export type SessionOverrides = Record<string, SessionOverride>;

/**
 * Overlays local edits onto the sessions returned by the API, before they
 * become grid events. Returns the input untouched when there's nothing to
 * apply, so the downstream `useMemo` chain doesn't recompute on every render.
 */
export function applySessionOverrides(
  blocks: WeekBlockResponse[] | undefined,
  overrides: SessionOverrides,
): WeekBlockResponse[] | undefined {
  if (!blocks || Object.keys(overrides).length === 0) return blocks;
  return blocks.map((block) => {
    if (!block.sessions.some((session) => overrides[session.id])) return block;
    return {
      ...block,
      sessions: block.sessions.map((session) => {
        const override = overrides[session.id];
        return override ? { ...session, ...override } : session;
      }),
    };
  });
}

/** Maps the drawer form's ids/codes back to the session entities they name. */
export interface OverrideLookups {
  teachersById: Map<string, TeacherBase>;
  roomsById: Map<string, RoomBase>;
  subjectsByName: Map<string, SubjectBase>;
  classesByCode: Map<string, ClassBase>;
}

/**
 * Resolves the drawer form into a session override — the live preview the
 * grid renders while editing. Only entities present in the lookups survive;
 * the UC is left untouched when its name isn't a known subject.
 */
export function buildSessionOverride(
  form: EventDrawerFormState,
  lookups: OverrideLookups,
): SessionOverride {
  const override: SessionOverride = {
    weekday: form.selectedWeekday,
    start_time: timeToHhmm(form.startTime),
    duration: form.durationSlots,
    teachers: form.selectedDocenteOverride
      .map((id) => lookups.teachersById.get(id))
      .filter((teacher): teacher is TeacherBase => teacher !== undefined),
    rooms: form.selectedSalaOverride
      .map((id) => lookups.roomsById.get(id))
      .filter((room): room is RoomBase => room !== undefined),
    classes: form.selectedTurmasOverride
      .map((code) => lookups.classesByCode.get(code))
      .filter((classItem): classItem is ClassBase => classItem !== undefined),
  };
  const subject = lookups.subjectsByName.get(form.selectedUcOverride);
  if (subject) override.subjects = [subject];
  return override;
}

/** Committed session edits for the schedule page. Cleared on unmount/course change by the caller. */
export function useLocalSessionEdits() {
  const [overrides, setOverrides] = useState<SessionOverrides>({});

  const commit = (sessionId: string, override: SessionOverride) => {
    setOverrides((prev) => ({ ...prev, [sessionId]: { ...prev[sessionId], ...override } }));
  };

  return { overrides, commit, clear: () => setOverrides({}) };
}
