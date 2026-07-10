import { useMemo } from "react";
import { COURSE_GROUPS, compareCourseAcronyms, getCourseGroupLabel } from "@/utils/scheduleEvents";
import type { CourseGroup, CourseOption } from "./types";

type DegreeOption = { acronym: string; name: string };
type TeacherOption = { id: string; acronym: string; name: string };
type RoomOption = { id: string; name: string; type: string | null; seats: string | null };

interface UseScheduleOptionsParams {
  degrees: DegreeOption[] | undefined;
  teachers: TeacherOption[] | undefined;
  rooms: RoomOption[] | undefined;
}

/**
 * Derives the static option lists fed to the navbar / edit-drawer dropdowns
 * from the project-level entity queries. Each input list is sorted by its
 * display key (acronym/name) and the degrees are bucketed into the
 * Licenciaturas / Mestrados / Pós-Graduações / Outros groups.
 */
export function useScheduleOptions({ degrees, teachers, rooms }: UseScheduleOptionsParams) {
  const courseOptions = useMemo<CourseGroup[]>(() => {
    const degreeOptions: CourseOption[] = (degrees ?? []).map((degree) => ({
      value: degree.acronym,
      label: degree.acronym,
      description: degree.name,
    }));

    const groupedByLabel = new Map<string, CourseOption[]>();
    for (const option of degreeOptions) {
      const groupLabel = getCourseGroupLabel(option.description ?? option.label);
      const current = groupedByLabel.get(groupLabel) ?? [];
      groupedByLabel.set(groupLabel, [...current, option]);
    }

    // Each group sorts on its own: pinned acronyms first (PI ToDo #15),
    // remaining ones alphabetical.
    return COURSE_GROUPS.map((label) => {
      const compare = compareCourseAcronyms(label);
      return {
        label,
        options: (groupedByLabel.get(label) ?? [])
          .slice()
          .sort((a, b) => compare(a.label, b.label)),
      };
    }).filter((group) => group.options.length > 0);
  }, [degrees]);

  const teacherOptions = useMemo(
    () =>
      (teachers ?? [])
        .slice()
        .sort((a, b) => a.acronym.localeCompare(b.acronym))
        .map((teacher) => ({
          id: teacher.id,
          acronym: teacher.acronym,
          label: `${teacher.acronym} - ${teacher.name}`,
        })),
    [teachers],
  );

  const roomOptions = useMemo(
    () =>
      (rooms ?? [])
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((room) => ({
          id: room.id,
          label: room.name,
          type: room.type ?? "",
          seats: room.seats,
        })),
    [rooms],
  );

  return { courseOptions, teacherOptions, roomOptions };
}
