import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useProject } from "@/api/hooks/project/project";
import { ROUTES } from "@/routes";
import { buildPath } from "@/utils/routes";

/**
 * Loads the project and gates access to the pages that only make sense once the
 * import has finished (the schedule and the parallel-sessions selection):
 *
 * - if no `projectId` is provided, redirects to `HOME`;
 * - if the project loads but its ingestion isn't finished, redirects to the
 *   project's dashboard;
 * - otherwise returns the query state so the caller can render a project-
 *   level loading or error placeholder.
 */
export function useProjectAccess(projectId: string | undefined) {
  const navigate = useNavigate();
  const { data: project, isPending, isError } = useProject(projectId ?? "");

  useEffect(() => {
    if (!projectId) {
      void navigate(ROUTES.HOME, { replace: true });
      return;
    }
    if (!project) return;
    const isReady = !!project.ingestion_finished_at;
    if (!isReady) void navigate(buildPath(ROUTES.DASHBOARD, { projectId }), { replace: true });
  }, [project, projectId, navigate]);

  return { project, isPending, isError };
}
