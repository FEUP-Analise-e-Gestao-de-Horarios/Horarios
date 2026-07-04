import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Layers } from "lucide-react";
import { toast } from "sonner";
import type { Project } from "@/types/project/project";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";

// Shared toast id so opening the schedule then the dashboard (or vice-versa)
// refreshes the same reminder instead of stacking a second one.
const REMINDER_TOAST_ID = "parallel-sessions-reminder";

/**
 * Whether a loaded project warrants the parallel-selection nudge: its ingestion
 * has finished (so there is something to select, and the schedule page won't
 * redirect it to the dashboard) but the selection step hasn't been done.
 */
export function shouldRemindParallelSelection(project: Project | undefined): project is Project {
  return !!project && !!project.ingestion_finished_at && !project.has_selected_parallel_sessions;
}

/**
 * Nudges the user toward the parallel-selection step when a ready project still
 * hasn't had it done. Used by the schedule and dashboard pages — the two places
 * a project's schedule is viewed — with an action that jumps to the selection
 * page. Fires once per project per mount so refetches don't re-toast.
 *
 * Rendered as a plain toast (not `warning`) wearing the `app-toast-reminder`
 * class: a calm dark card with a terracotta accent rather than the saturated
 * per-type fills, since this is a gentle nudge and not an alert.
 */
export function useParallelSessionsReminder(project: Project | undefined) {
  const navigate = useNavigate();
  const remindedProjectId = useRef<number | null>(null);

  useEffect(() => {
    if (!shouldRemindParallelSelection(project)) return;
    // A refetch hands back a new object reference; keep it to one toast per project.
    if (remindedProjectId.current === project.id) return;
    remindedProjectId.current = project.id;

    toast("Aulas em paralelo", {
      id: REMINDER_TOAST_ID,
      className: "app-toast-reminder",
      description: "Ainda não selecionaste as aulas em paralelo deste projeto.",
      icon: <Layers size={16} strokeWidth={2.25} aria-hidden />,
      duration: 8000,
      action: {
        label: "Selecionar",
        onClick: () =>
          void navigate(buildPath(ROUTES.PARALLEL_SESSIONS, { projectId: String(project.id) })),
      },
    });
  }, [project, navigate]);
}
