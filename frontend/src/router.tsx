import { createBrowserRouter } from "react-router-dom";
import ReactTest1Page from "./pages/ReactTest1Page";
import ReactTest2Page from "./pages/ReactTest2Page";

// Paths here must match what Django delegates to spa_view in urls.py
export const router = createBrowserRouter([
  { path: "/react-test", element: <ReactTest1Page /> },
  { path: "/react-test-2", element: <ReactTest2Page /> },
]);
