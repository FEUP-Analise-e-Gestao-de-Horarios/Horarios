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

/** A project mid-ingestion: started, but not yet finished or failed. */
export function isProjectProcessing(project: Project | undefined): project is Project {
  return (
    !!project &&
    !!project.ingestion_started_at &&
    !project.ingestion_finished_at &&
    !project.ingestion_failed_at
  );
}

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
 * When the dashboard watches a project finish ingesting live (it polls while
 * processing), the toast reads as a completion — "ready now" — rather than the
 * passive "you still haven't selected" nudge shown when landing on a project
 * that was already finished.
 *
 * Rendered as a plain (default-type) toast so it wears the shared neutral card
 * with a monochrome icon, rather than a coloured per-type accent — this is a
 * gentle nudge, not an alert.
 */
export function useParallelSessionsReminder(project: Project | undefined) {
  const navigate = useNavigate();
  const remindedProjectId = useRef<number | null>(null);
  // Which project we've watched ingest this mount, so finishing it live reads as
  // a completion rather than the passive revisit nudge.
  const watchedIngestingId = useRef<number | null>(null);

  useEffect(() => {
    if (isProjectProcessing(project)) {
      watchedIngestingId.current = project.id;
    }

    if (!shouldRemindParallelSelection(project)) return;
    // A refetch hands back a new object reference; keep it to one toast per project.
    if (remindedProjectId.current === project.id) return;
    remindedProjectId.current = project.id;

    const justFinished = watchedIngestingId.current === project.id;
    const { title, description, duration } = justFinished
      ? {
          title: "Projeto pronto",
          description: "O processamento terminou. Já podes selecionar as aulas em paralelo.",
          duration: 6000,
        }
      : {
          title: "Aulas em paralelo",
          description: "Ainda não selecionaste as aulas em paralelo deste projeto.",
          duration: 4500,
        };

    toast(title, {
      id: REMINDER_TOAST_ID,
      description,
      icon: <Layers size={16} strokeWidth={2.25} aria-hidden />,
      duration,
      action: {
        label: "Selecionar",
        onClick: () =>
          void navigate(buildPath(ROUTES.PARALLEL_SESSIONS, { projectId: String(project.id) })),
      },
    });
  }, [project, navigate]);
}
