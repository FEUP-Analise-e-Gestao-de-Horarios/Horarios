import { createBrowserRouter } from "react-router-dom";
import Login from "./pages/Login";
import ReactTest2Page from "./pages/ReactTest2Page";

// Paths here must match what Django delegates to spa_view in urls.py
export const router = createBrowserRouter([
  { path: "/react-login", element: <Login /> },
  { path: "/react-test-2", element: <ReactTest2Page /> },
]);
