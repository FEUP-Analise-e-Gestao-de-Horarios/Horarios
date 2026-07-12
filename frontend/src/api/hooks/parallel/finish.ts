import { type Dispatch, type SetStateAction, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";
import { ROUTES } from "@/routes";
import { queryKeys } from "@/api/queryKeys";
import type { ParallelCandidateGraph, UUID } from "@/types/parallelSessions";
import type { Project } from "@/types/project/project";
import { getErrorMessage } from "@/api/errors";
import { handleStaleConfirmError, type StaleConfirmScope } from "./errors";
import type { SavingControls } from "./saving";

/** Owns the finish/stale/reset/navigation flow: the finish + reset modals, the
 * "mark step done and leave" writes, the confirm-all-and-finish action (with
 * stale handling), plain navigation (remembering the view), and the reset. */
export function useParallelFinish(params: {
  projectId: string | undefined;
  projectIdNum: number;
  projectValid: boolean;
  graphs: ParallelCandidateGraph[];
  allYearsConfirmed: boolean;
  rememberView: () => void;
  saving: SavingControls;
  setConfirmedSubjectIds: Dispatch<SetStateAction<Set<UUID>>>;
  setStaleConfirmScope: Dispatch<SetStateAction<StaleConfirmScope>>;
}) {
  const {
    projectId,
    projectIdNum,
    projectValid,
    graphs,
    allYearsConfirmed,
    rememberView,
    setConfirmedSubjectIds,
    setStaleConfirmScope,
  } = params;
  const { beginRequest, endRequest } = params.saving;
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [showResetModal, setShowResetModal] = useState(false);
  const [showFinishModal, setShowFinishModal] = useState(false);

  const backRoute = ROUTES.SCHEDULE.replace(":projectId", projectId ?? "");

  // Flip the cached project's flag right away so the schedule page — which reads
  // the (inactive) detail query from cache — doesn't fire the "review parallel
  // sessions" reminder off stale data before the background refetch lands.
  const markDetailSelected = () => {
    queryClient.setQueryData<Project>(
      queryKeys.projects.detail(projectId ?? String(projectIdNum)),
      (old) => (old ? { ...old, has_selected_parallel_sessions: true } : old),
    );
  };

  const handleBack = () => {
    rememberView();
    void navigate(backRoute);
  };

  const handleNavigateHome = () => {
    rememberView();
    void navigate(ROUTES.HOME);
  };

  const handleNavigateDashboard = () => {
    rememberView();
    void navigate(ROUTES.DASHBOARD.replace(":projectId", projectId ?? ""));
  };

  const handleNavigateExport = () => {
    rememberView();
    void navigate(ROUTES.EXPORT.replace(":projectId", projectId ?? ""));
  };

  // Mark this project's parallel-selection step done, then leave for the
  // schedule. Set on every Terminar exit (confirmed or not) so the home card
  // stops routing back here; only leaves once the write lands.
  const markSelectedAndLeave = () => {
    if (!projectValid) return;
    beginRequest();
    api
      .post(`/api/projects/${projectIdNum}/parallel-blocks/finish`, {})
      .then(() => {
        markDetailSelected();
        // Refresh the project list so ProjectCard sees the updated flag.
        void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        setShowFinishModal(false);
        rememberView();
        void navigate(backRoute);
      })
      .catch((err: unknown) => {
        toast.error(getErrorMessage(err, "Erro ao terminar"));
      })
      .finally(endRequest);
  };

  // Finish: mark done and leave when every year (across all degrees) is
  // confirmed, otherwise open the prompt listing the years still pending.
  const handleFinish = () => {
    if (allYearsConfirmed) {
      markSelectedAndLeave();
    } else {
      setShowFinishModal(true);
    }
  };

  // "Confirm all and finish": mark every current candidate confirmed, flag the
  // step done, then leave. Sends the client's full candidate view so the server
  // can reject a stale set; only navigates once both writes land.
  const finishAndConfirmAll = () => {
    if (!projectValid) return;
    const candidateGroupIds = graphs.map((g) => g.candidate_group_id);
    beginRequest();
    api
      .post(`/api/projects/${projectIdNum}/parallel-blocks/confirmations/all`, {
        candidate_group_ids: candidateGroupIds,
      })
      .then(() => api.post(`/api/projects/${projectIdNum}/parallel-blocks/finish`, {}))
      .then(() => {
        setConfirmedSubjectIds(new Set(graphs.map((g) => g.subject.id)));
        markDetailSelected();
        // Drop the cached candidates payload so its confirmed flags are refetched.
        void queryClient.invalidateQueries({
          queryKey: queryKeys.projects.parallelCandidates(String(projectIdNum)),
        });
        // Refresh the project list so ProjectCard sees the updated flag.
        void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        setShowFinishModal(false);
        rememberView();
        void navigate(backRoute);
      })
      .catch((err: unknown) => {
        handleStaleConfirmError(err, {
          queryClient,
          projectIdNum,
          setStaleConfirmScope,
          scope: "all",
          onStale: () => setShowFinishModal(false),
        });
      })
      .finally(endRequest);
  };

  // Finish without confirming the rest: still marks the step done, so the user
  // won't be sent back here. Keeps the groups and confirmations already made.
  const finishContinue = () => {
    markSelectedAndLeave();
  };

  // Continue later: leave for the schedule (like the Horário button) without
  // marking the step done, so the home card routes back here next time.
  const finishLater = () => {
    setShowFinishModal(false);
    rememberView();
    void navigate(backRoute);
  };

  const handleReset = () => {
    if (!projectValid) return;
    setShowResetModal(true);
  };

  const confirmReset = () => {
    if (!projectValid) return;
    rememberView();
    // Recomeçar clears the confirmed groups, every subject confirmation, and the
    // "selection done" flag, so the project starts the step over from scratch.
    Promise.all([
      api.delete(`/api/projects/${projectIdNum}/parallel-blocks/groups/`),
      api.delete(`/api/projects/${projectIdNum}/parallel-blocks/confirmations/`),
      api.delete(`/api/projects/${projectIdNum}/parallel-blocks/finish`),
    ])
      .then(() => {
        void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        window.location.reload();
      })
      .catch((err: unknown) => {
        setShowResetModal(false);
        toast.error(getErrorMessage(err, "Erro ao recomeçar"));
      });
  };

  return {
    showResetModal,
    setShowResetModal,
    showFinishModal,
    setShowFinishModal,
    handleFinish,
    finishAndConfirmAll,
    finishContinue,
    finishLater,
    handleBack,
    handleNavigateHome,
    handleNavigateExport,
    handleNavigateDashboard,
    handleReset,
    confirmReset,
  };
}
