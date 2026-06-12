export interface SessionsQueryFilters {
  yearId: string;
  subjectIds: string[];
  classIds: string[];
  weekdays: string[];
}

export const queryKeys = {
  projects: {
    all: ["projects"] as const,
    detail: (id: string) => ["projects", id] as const,
    stats: (id: string) => ["projects", id, "stats"] as const,
    degrees: (id: string) => ["projects", id, "degrees"] as const,
    degree: (id: string, degreeId: string) => ["projects", id, "degrees", degreeId] as const,
    year: (id: string, yearId: string) => ["projects", id, "years", yearId] as const,
    teachers: (id: string) => ["projects", id, "teachers"] as const,
    teacher: (id: string, teacherId: string) => ["projects", id, "teachers", teacherId] as const,
    rooms: (id: string) => ["projects", id, "rooms"] as const,
    room: (id: string, roomId: string) => ["projects", id, "rooms", roomId] as const,
    subject: (id: string, subjectId: string) => ["projects", id, "subjects", subjectId] as const,
    class: (id: string, classId: string) => ["projects", id, "classes", classId] as const,
    // Prefix of every sessions(...) key; lets mutations invalidate all
    // session queries for a project at once.
    sessionsRoot: (id: string) => ["projects", id, "sessions"] as const,
    conflictsRoot: (id: string) => ["projects", id, "conflicts"] as const,
    conflicts: (id: string, scope: string, yearId: string, includeIgnored: boolean) =>
      ["projects", id, "conflicts", scope, yearId, includeIgnored] as const,
    permissions: (id: string) => ["projects", id, "permissions"] as const,
    parallelBlocks: (id: string, sessionId: string) =>
      ["projects", id, "parallel-blocks", sessionId] as const,
    sessions: (id: string, filters: SessionsQueryFilters) =>
      [
        "projects",
        id,
        "sessions",
        filters.yearId,
        [...filters.subjectIds].sort(),
        [...filters.classIds].sort(),
        [...filters.weekdays].sort(),
      ] as const,
  },
} as const;
