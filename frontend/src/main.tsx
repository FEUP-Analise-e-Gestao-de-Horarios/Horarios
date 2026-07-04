import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { queryClient } from "./api/queryClient";
import { router } from "./router";
import AltClickCopy from "./components/AltClickCopy";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <AltClickCopy />
      <Toaster
        position="top-right"
        toastOptions={{ className: "app-toast" }}
        style={{ "--width": "300px" } as React.CSSProperties}
      />
    </QueryClientProvider>
  </React.StrictMode>,
);
