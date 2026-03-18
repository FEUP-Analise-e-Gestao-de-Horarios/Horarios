import { createBrowserRouter } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import Dashboard from "./pages/Dashboard";
import ChangePassword from "./pages/ChangePassword";

// Paths here must match what Django delegates to spa_view in urls.py
export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/forgot-password", element: <ForgotPasswordPage /> },
  
  { path: "/react-dashboard", element: <Dashboard /> },
  { path: "/react-change-password", element: <ChangePassword /> },
]);
