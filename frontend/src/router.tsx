import { createBrowserRouter } from "react-router-dom";
import { requireAuth } from "./api/auth";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import HomePage from "./pages/HomePage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import { ROUTES } from "./routes";
import SchedulePage from "./pages/SchedulePage";
import DashboardPage from "./pages/DashboardPage";

// Paths here must match what Django delegates to spa_view in urls.py
export const router = createBrowserRouter([
  { path: ROUTES.HOME, element: <HomePage />, loader: requireAuth },

  { path: ROUTES.LOGIN, element: <LoginPage /> },
  { path: ROUTES.FORGOT_PASSWORD, element: <ForgotPasswordPage /> },
  { path: ROUTES.CHANGE_PASSWORD, element: <ChangePasswordPage />, loader: requireAuth },

  { path: ROUTES.SCHEDULE, element: <SchedulePage /> },
  { path: ROUTES.DASHBOARD, element: <DashboardPage />, loader: requireAuth },
]);
