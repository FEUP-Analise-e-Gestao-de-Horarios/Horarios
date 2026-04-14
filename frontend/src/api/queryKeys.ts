export const queryKeys = {
  projects: {
    all: ["projects"] as const,
    detail: (id: string) => ["projects", id] as const,
    stats: (id: string) => ["projects", id, "stats"] as const,
    degrees: (id: string) => ["projects", id, "degrees"] as const,
    degree: (id: string, degreeId: string) => ["projects", id, "degrees", degreeId] as const,
    teachers: (id: string) => ["projects", id, "teachers"] as const,
    teacher: (id: string, teacherId: string) => ["projects", id, "teachers", teacherId] as const,
    rooms: (id: string) => ["projects", id, "rooms"] as const,
    room: (id: string, roomId: string) => ["projects", id, "rooms", roomId] as const,
  },
} as const;
