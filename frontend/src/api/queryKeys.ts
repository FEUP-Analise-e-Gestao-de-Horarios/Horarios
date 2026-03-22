export const queryKeys = {
  projects: {
    all: ["projects"] as const,
    detail: (id: string) => ["projects", id] as const,
    stats: (id: string) => ["projects", id, "stats"] as const,
    degrees: (id: string) => ["projects", id, "degrees"] as const,
    teachers: (id: string) => ["projects", id, "teachers"] as const,
    rooms: (id: string) => ["projects", id, "rooms"] as const,
  },
} as const;
