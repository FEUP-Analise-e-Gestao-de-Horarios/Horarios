import { type Dispatch, type SetStateAction } from "react";
import { useParams } from "react-router-dom";
import {
  type DegreeOption,
  type ParallelCandidateGraph,
  type UnconfirmedDegree,
  type UUID,
  type YearOption,
} from "@/types/parallelSessions";
import { useParallelCandidatesQuery } from "./parallel/useParallelCandidatesQuery";
import { useParallelFilters } from "./parallel/useParallelFilters";
import { useParallelGroups, type GroupView } from "./parallel/useParallelGroups";
import { useParallelSelection } from "./parallel/useParallelSelection";
import { useParallelConfirmations } from "./parallel/useParallelConfirmations";
import { useParallelFinish } from "./parallel/useParallelFinish";
import { useSaving } from "./parallel/useSaving";

// Re-exported so the candidate/group components can keep importing it from here.
export type { GroupView } from "./parallel/useParallelGroups";

export interface UseParallelSessionsReturn {
  degrees: DegreeOption[];
  loadingDegrees: boolean;
  degreesError: string | null;
  selectedDegree: DegreeOption | null;

  selectedYearIds: Set<UUID>;
  yearsWithCandidates: YearOption[];

  loadingCandidates: boolean;
  candidatesError: string | null;
  /** Candidate graphs visible under the current degree/year filter. */
  visibleGraphs: ParallelCandidateGraph[];

  /** Blocks already assigned to a draft/confirmed group (locked in the graph). */
  assignedBlockIds: Set<UUID>;
  /** Per-component in-progress selection. */
  selectionByGroup: Record<UUID, Set<UUID>>;
  /** Whether the current selection for a component is a valid (connected, ≥2) group. */
  isSelectionValid: (candidateGroupId: UUID) => boolean;
  /** Whether all still-unassigned nodes of a component form a valid group. */
  canGroupAll: (candidateGroupId: UUID) => boolean;

  groupViewsBySubject: Map<string, GroupView[]>;

  /** True while any create/delete request is in flight. */
  saving: boolean;

  showResetModal: boolean;
  setShowResetModal: Dispatch<SetStateAction<boolean>>;

  /** Subject ids the user has marked reviewed/confirmed. */
  confirmedSubjectIds: Set<UUID>;
  /** Year ids all of whose subjects are confirmed (across every degree). */
  confirmedYearIds: Set<UUID>;
  /** Degree ids all of whose years are confirmed. */
  confirmedDegreeIds: Set<UUID>;
  /** Confirm a subject; resolves false (rolled back) if the request was rejected. */
  confirmSubject: (subjectId: UUID) => Promise<boolean>;
  unconfirmSubject: (subjectId: UUID) => void;
  /** True when every year with candidates (all degrees) is confirmed. */
  allYearsConfirmed: boolean;
  /** Degrees with unconfirmed years, for the finish prompt. */
  unconfirmedByDegree: UnconfirmedDegree[];

  showFinishModal: boolean;
  setShowFinishModal: Dispatch<SetStateAction<boolean>>;
  /** Shown when a confirm was rejected as stale; the list has been refetched. */
  /** Which confirm was rejected as stale (drives the prompt copy), or null. */
  staleConfirmScope: "subject" | "all" | null;
  setStaleConfirmScope: Dispatch<SetStateAction<"subject" | "all" | null>>;
  /** Terminar: mark done and leave if all confirmed, else open the finish prompt. */
  handleFinish: () => void;
  /** Confirm everything, mark the step done, then leave for the schedule. */
  finishAndConfirmAll: () => void;
  /** Mark the step done and leave without confirming the rest (won't be asked again). */
  finishContinue: () => void;
  /** Leave for the schedule without marking the step done (asked again next time). */
  finishLater: () => void;

  handleDegreeClick: (degree: DegreeOption) => void;
  handleYearSelect: (yearId: UUID) => void;
  handleToggleNode: (candidateGroupId: UUID, blockId: UUID) => void;
  /** Create a group from the current selection; returns its id, or null if invalid. */
  handleCreateGroup: (candidateGroupId: UUID) => UUID | null;
  /** Group all still-free nodes of a component; returns its id, or null if invalid. */
  handleGroupAll: (candidateGroupId: UUID) => UUID | null;
  handleRemoveGroup: (groupId: string) => void;
  handleBack: () => void;
  handleNavigateHome: () => void;
  handleReset: () => void;
  confirmReset: () => void;
}

/**
 * Thin orchestrator over the `parallel/` sub-hooks. Composes them in a single
 * one-way data flow — query → filters → groups → selection → confirmations →
 * finish — and wires the few handlers that cross a boundary (create/group-all
 * validate via selection then call the groups primitive; degree change also
 * clears the selection). Returns the flat public API the page consumes.
 */
export function useParallelSessions(): UseParallelSessionsReturn {
  const { projectId } = useParams<{ projectId: string }>();
  const projectIdNum = Number(projectId);
  const candidatesEnabled = Boolean(projectId) && !Number.isNaN(projectIdNum);

  const { candidatesData, graphs, loadingCandidates, candidatesError } = useParallelCandidatesQuery(
    projectIdNum,
    candidatesEnabled,
  );

  const filters = useParallelFilters(projectId, graphs);

  const saving = useSaving();

  const groups = useParallelGroups({
    projectIdNum,
    candidatesData,
    loadingCandidates,
    graphs,
    selectedYearIds: filters.selectedYearIds,
    saving,
  });

  // Selection is created after groups so it receives `assignedBlockIds`; it
  // knows nothing about persistence, breaking the selection↔groups cycle.
  const selection = useParallelSelection(graphs, groups.assignedBlockIds);

  const confirmations = useParallelConfirmations({
    projectId,
    projectIdNum,
    candidatesData,
    loadingCandidates,
    graphs,
    saving,
  });

  const finish = useParallelFinish({
    projectId,
    projectIdNum,
    graphs,
    allYearsConfirmed: confirmations.allYearsConfirmed,
    rememberView: filters.rememberView,
    saving,
    setConfirmedSubjectIds: confirmations.setConfirmedSubjectIds,
    setStaleConfirmScope: confirmations.setStaleConfirmScope,
  });

  // Selecting a degree also clears the in-progress node selection.
  const handleDegreeClick = (degree: DegreeOption) => {
    filters.handleDegreeClick(degree);
    selection.clearSelection();
  };

  // Create a group from the current selection: validate via selection, hand the
  // block ids to the groups primitive, then clear that component's selection.
  const handleCreateGroup = (candidateGroupId: UUID): UUID | null => {
    if (!selection.isSelectionValid(candidateGroupId)) return null;
    const blockIds = selection.selectionBlockIds(candidateGroupId);
    const id = groups.createGroup(candidateGroupId, blockIds);
    selection.clearSelectionFor(candidateGroupId);
    return id;
  };

  // Group every still-unassigned node of a component in one action.
  const handleGroupAll = (candidateGroupId: UUID): UUID | null => {
    if (!selection.canGroupAll(candidateGroupId)) return null;
    const blockIds = selection.unassignedBlockIds(candidateGroupId);
    const id = groups.createGroup(candidateGroupId, blockIds);
    selection.clearSelectionFor(candidateGroupId);
    return id;
  };

  return {
    degrees: filters.degrees,
    loadingDegrees: loadingCandidates,
    degreesError: candidatesError,
    selectedDegree: filters.selectedDegree,
    selectedYearIds: filters.selectedYearIds,
    yearsWithCandidates: filters.yearsWithCandidates,
    loadingCandidates,
    candidatesError,
    visibleGraphs: filters.visibleGraphs,
    assignedBlockIds: groups.assignedBlockIds,
    selectionByGroup: selection.selectionByGroup,
    isSelectionValid: selection.isSelectionValid,
    canGroupAll: selection.canGroupAll,
    groupViewsBySubject: groups.groupViewsBySubject,
    saving: saving.saving,
    showResetModal: finish.showResetModal,
    setShowResetModal: finish.setShowResetModal,
    confirmedSubjectIds: confirmations.confirmedSubjectIds,
    confirmedYearIds: confirmations.confirmedYearIds,
    confirmedDegreeIds: confirmations.confirmedDegreeIds,
    confirmSubject: confirmations.confirmSubject,
    unconfirmSubject: confirmations.unconfirmSubject,
    allYearsConfirmed: confirmations.allYearsConfirmed,
    unconfirmedByDegree: confirmations.unconfirmedByDegree,
    showFinishModal: finish.showFinishModal,
    setShowFinishModal: finish.setShowFinishModal,
    staleConfirmScope: confirmations.staleConfirmScope,
    setStaleConfirmScope: confirmations.setStaleConfirmScope,
    handleFinish: finish.handleFinish,
    finishAndConfirmAll: finish.finishAndConfirmAll,
    finishContinue: finish.finishContinue,
    finishLater: finish.finishLater,
    handleDegreeClick,
    handleYearSelect: filters.handleYearSelect,
    handleToggleNode: selection.handleToggleNode,
    handleCreateGroup,
    handleGroupAll,
    handleRemoveGroup: groups.handleRemoveGroup,
    handleBack: finish.handleBack,
    handleNavigateHome: finish.handleNavigateHome,
    handleReset: finish.handleReset,
    confirmReset: finish.confirmReset,
  };
}
