import { useEffect, useState } from "react";

const CHANGE_EVENT = "dashboard-conflict-highlights-change";

function storageKey(projectId: string): string {
  return `dashboard-conflict-highlights:${projectId}`;
}

export function useDashboardConflictHighlights(projectId: string) {
  const key = storageKey(projectId);
  const [enabled, setEnabled] = useState(() => localStorage.getItem(key) === "true");

  useEffect(() => {
    const sync = () => setEnabled(localStorage.getItem(key) === "true");
    window.addEventListener(CHANGE_EVENT, sync);
    window.addEventListener("storage", sync);
    sync();
    return () => {
      window.removeEventListener(CHANGE_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, [key]);

  const toggle = () => {
    const next = localStorage.getItem(key) !== "true";
    localStorage.setItem(key, String(next));
    window.dispatchEvent(new Event(CHANGE_EVENT));
  };

  return { enabled, toggle };
}
