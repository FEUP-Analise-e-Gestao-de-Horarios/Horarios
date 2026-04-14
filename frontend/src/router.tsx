import { createBrowserRouter } from "react-router-dom";
import { redirectIfAuthenticated, requireAuth } from "./api/auth";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import HomePage from "./pages/HomePage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import { ROUTES } from "./routes";
import SchedulePage from "./pages/SchedulePage";
import DashboardPage from "./pages/DashboardPage";
import DegreeDetailPage from "./pages/DegreeDetailPage";
import TeacherDetailPage from "./pages/TeacherDetailPage";
import RoomDetailPage from "./pages/RoomDetailPage";

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
  { path: ROUTES.DEGREE_DETAIL, element: <DegreeDetailPage />, loader: requireAuth },
  { path: ROUTES.TEACHER_DETAIL, element: <TeacherDetailPage />, loader: requireAuth },
  { path: ROUTES.ROOM_DETAIL, element: <RoomDetailPage />, loader: requireAuth },
]);
