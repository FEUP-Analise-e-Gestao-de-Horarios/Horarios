import { createBrowserRouter } from "react-router-dom";
import { redirectIfAuthenticated, requireAuth } from "./api/auth";
import LoginPage from "./pages/auth/LoginPage";
import ForgotPasswordPage from "./pages/auth/ForgotPasswordPage";
import HomePage from "./pages/HomePage";
import ChangePasswordPage from "./pages/auth/ChangePasswordPage";
import { ROUTES } from "./routes";
import SchedulePage from "./pages/SchedulePage";
import DashboardPage from "./pages/dashboard/DashboardPage";
import ExportSessionContextPage from "./pages/dashboard/ExportSessionContextPage";
import DegreeDetailPage from "./pages/dashboard/DegreeDetailPage";
import TeacherDetailPage from "./pages/dashboard/TeacherDetailPage";
import RoomDetailPage from "./pages/dashboard/RoomDetailPage";
import SubjectDetailPage from "./pages/dashboard/SubjectDetailPage";
import ClassDetailPage from "./pages/dashboard/ClassDetailPage";
import ExporterPage from "./pages/ExporterPage";
import ParallelSessionsPage from "./pages/ParallelSessionsPage";

// Paths here must match what Django delegates to spa_view in urls.py
export const router = createBrowserRouter([
  { path: ROUTES.HOME, element: <HomePage />, loader: requireAuth },

  { path: ROUTES.LOGIN, element: <LoginPage />, loader: redirectIfAuthenticated },
  {
    path: ROUTES.FORGOT_PASSWORD,
    element: <ForgotPasswordPage />,
    loader: redirectIfAuthenticated,
  },
  { path: ROUTES.CHANGE_PASSWORD, element: <ChangePasswordPage />, loader: requireAuth },

  { path: ROUTES.SCHEDULE, element: <SchedulePage />, loader: requireAuth },
  { path: ROUTES.DASHBOARD, element: <DashboardPage />, loader: requireAuth },
  {
    path: ROUTES.EXPORT_SESSION_CONTEXT,
    element: <ExportSessionContextPage />,
    loader: requireAuth,
  },
  { path: ROUTES.DEGREE_DETAIL, element: <DegreeDetailPage />, loader: requireAuth },
  { path: ROUTES.TEACHER_DETAIL, element: <TeacherDetailPage />, loader: requireAuth },
  { path: ROUTES.ROOM_DETAIL, element: <RoomDetailPage />, loader: requireAuth },
  { path: ROUTES.SUBJECT_DETAIL, element: <SubjectDetailPage />, loader: requireAuth },
  { path: ROUTES.CLASS_DETAIL, element: <ClassDetailPage />, loader: requireAuth },
  { path: ROUTES.EXPORT, element: <ExporterPage />, loader: requireAuth },
  { path: ROUTES.PARALLEL_SESSIONS, element: <ParallelSessionsPage />, loader: requireAuth },
]);
