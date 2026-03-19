import { createBrowserRouter } from "react-router-dom";
import LoginPage from "./pages/LoginPage";

// Paths here must match what Django delegates to spa_view in urls.py
export const router = createBrowserRouter([{ path: "/login", element: <LoginPage /> }]);
