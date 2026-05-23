export const ROUTES = {
  HOME: "/",
  LOGIN: "/login",
  FORGOT_PASSWORD: "/forgot-password",
  CHANGE_PASSWORD: "/change-password",
  SCHEDULE: "/projects/:projectId",
  DASHBOARD: "/projects/:projectId/dashboard",
  DEGREE_DETAIL: "/projects/:projectId/dashboard/degrees/:degreeId",
  TEACHER_DETAIL: "/projects/:projectId/dashboard/teachers/:teacherId",
  ROOM_DETAIL: "/projects/:projectId/dashboard/rooms/:roomId",
  SUBJECT_DETAIL: "/projects/:projectId/dashboard/subjects/:subjectId",
  CLASS_DETAIL: "/projects/:projectId/dashboard/classes/:classId",
  EXPORT: "/projects/:projectId/export",
} as const;
