import { useMemo, useState } from "react";
import { useParallelSessions } from "@/api/hooks/parallel/sessions";
import { DAY_ORDER, type ParallelCandidateGraph, type UUID } from "@/types/parallelSessions";
import { EMPTY_SELECTION, graphStartTime } from "./parallelDisplay";
import { useGroupReveal } from "./useGroupReveal";

/**
 * Page-level ViewModel for the parallel-sessions page. Wraps the
 * {@link useParallelSessions} orchestrator with the presentation concerns the
 * page itself used to carry: the per-year / per-subject selection memory, the
 * subject-id-keyed derivations that drive the selectors and panels, the
 * confirm/reset/select workflows, and the group-reveal choreography. The page
 * component consumes this and does nothing but render.
 */
export function useParallelSessionsView() {
  const session = useParallelSessions();

  // Per-subject memory of which candidate's graph is open, mirroring how the
  // year is remembered per degree and the subject per year. Keyed by subject id.
  const [selectedCandidateBySubject, setSelectedCandidateBySubject] = useState<
    Record<UUID, string | null>
  >({});
  // Per-year memory of the chosen subject id.
  const [selectedSubjectByYear, setSelectedSubjectByYear] = useState<Record<UUID, UUID>>({});

  // Group the visible candidate components by subject id, sorted for display.
  const graphsBySubject = useMemo(() => {
    const map = new Map<UUID, ParallelCandidateGraph[]>();
    for (const g of session.visibleGraphs) {
      const list = map.get(g.subject.id);
      if (list) list.push(g);
      else map.set(g.subject.id, [g]);
    }
    for (const list of map.values()) {
      list.sort(
        (a, b) =>
          (DAY_ORDER[a.weekday] ?? 99) - (DAY_ORDER[b.weekday] ?? 99) ||
          graphStartTime(a) - graphStartTime(b),
      );
    }
    return map;
  }, [session.visibleGraphs]);

  // Subjects for the left-column selector, each with its display metadata,
  // alphabetically sorted by name. Replaces the old name-keyed bridge maps.
  const subjects = useMemo(() => {
    const map = new Map<UUID, { id: UUID; name: string; acronym: string }>();
    for (const g of session.visibleGraphs) {
      if (!map.has(g.subject.id))
        map.set(g.subject.id, {
          id: g.subject.id,
          name: g.subject.name,
          acronym: g.subject.acronym,
        });
    }
    return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [session.visibleGraphs]);

  // Degrees for the left-column selector, alphabetically sorted by acronym.
  const sortedDegrees = useMemo(
    () => [...session.degrees].sort((a, b) => a.acronym.localeCompare(b.acronym)),
    [session.degrees],
  );

  // The single selected year driving the candidate list.
  const activeYearId =
    session.yearsWithCandidates.find((y) => session.selectedYearIds.has(y.id))?.id ?? null;

  // Resolve the effective subject: the one remembered for the active year when it
  // still exists, else the first available (e.g. after a degree/year change).
  const rememberedSubjectId = activeYearId ? selectedSubjectByYear[activeYearId] : undefined;
  const activeSubjectId =
    rememberedSubjectId && subjects.some((s) => s.id === rememberedSubjectId)
      ? rememberedSubjectId
      : (subjects[0]?.id ?? null);
  const activeSubjectName = activeSubjectId
    ? (subjects.find((s) => s.id === activeSubjectId)?.name ?? null)
    : null;

  const subjectGraphs = activeSubjectId ? (graphsBySubject.get(activeSubjectId) ?? []) : [];

  // The open candidate, remembered per subject and constrained to it so a graph
  // only stays selected while its subject is active.
  const selectedCandidateId = activeSubjectId
    ? (selectedCandidateBySubject[activeSubjectId] ?? null)
    : null;

  const {
    groupsScrollRef,
    activeGroupColRef,
    highlightedGroupId,
    registerGroupRef,
    revealGroup,
    scrollGroupIntoView,
    handleRevealGroup,
  } = useGroupReveal(activeSubjectId, session.groupViewsBySubject);

  // Candidate id -> ids of the groups already carved out of it.
  const groupIdsByCandidate = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const items of session.groupViewsBySubject.values())
      for (const view of items) {
        const arr = map.get(view.group.candidateGroupId);
        if (arr) arr.push(view.group.id);
        else map.set(view.group.candidateGroupId, [view.group.id]);
      }
    return map;
  }, [session.groupViewsBySubject]);

  const activeSubjectConfirmed = activeSubjectId
    ? session.confirmedSubjectIds.has(activeSubjectId)
    : false;
  // The groups already created for the active subject (in the current year).
  const activeSubjectGroupViews = activeSubjectId
    ? (session.groupViewsBySubject.get(activeSubjectId) ?? [])
    : [];

  // Remember the chosen subject for the active year.
  const handleSelectSubject = (subjectId: UUID) => {
    if (activeYearId) setSelectedSubjectByYear((prev) => ({ ...prev, [activeYearId]: subjectId }));
  };

  // Confirm the active subject, then jump the selector to the next subject that
  // is still unconfirmed (searching forward from the current one, then wrapping).
  // If the confirm is rejected, the optimistic jump is reverted.
  const handleConfirmActiveSubject = () => {
    if (!activeSubjectId) return;
    const prevSubjectId = activeSubjectId;
    const yearId = activeYearId;
    const confirmedNow = new Set(session.confirmedSubjectIds).add(activeSubjectId);
    const idx = subjects.findIndex((s) => s.id === activeSubjectId);
    const ordered = [...subjects.slice(idx + 1), ...subjects.slice(0, idx)];
    const next = ordered.find((s) => !confirmedNow.has(s.id));
    void session.confirmSubject(activeSubjectId).then((ok) => {
      // On failure undo the jump, but only if the user hasn't since moved on.
      if (!ok && next && yearId) {
        setSelectedSubjectByYear((prev) =>
          prev[yearId] === next.id ? { ...prev, [yearId]: prevSubjectId } : prev,
        );
      }
    });
    if (next && yearId) {
      setSelectedSubjectByYear((prev) => ({ ...prev, [yearId]: next.id }));
    }
  };

  // Repor: drop every group already formed for the active subject in one batch,
  // so the whole reset triggers a single cache invalidation instead of one per
  // group.
  const handleResetActiveSubject = () => {
    session.handleRemoveGroups(activeSubjectGroupViews.map((view) => view.group.id));
  };

  // Undo confirmation (fired by clicking the confirmed button, which reddens on
  // hover to signal the destructive action).
  const handleUnconfirmActiveSubject = () => {
    if (activeSubjectId) session.unconfirmSubject(activeSubjectId);
  };

  // Open/close a candidate's graph, remembered per subject. Opening one that
  // already has exactly one group also jumps to that group.
  const handleSelectCandidate = (candidateId: string) => {
    if (!activeSubjectId) return;
    const closing = selectedCandidateBySubject[activeSubjectId] === candidateId;
    setSelectedCandidateBySubject((prev) => ({
      ...prev,
      [activeSubjectId]: closing ? null : candidateId,
    }));
    if (!closing) {
      const ids = groupIdsByCandidate.get(candidateId);
      if (ids && ids.length === 1) revealGroup(ids[0]!);
    }
  };

  // The candidate currently driving the graph panel, resolved within the active
  // subject so it collapses when its subject (or year) is no longer selected.
  const selectedGraph =
    (selectedCandidateId &&
      subjectGraphs.find((g) => g.candidate_group_id === selectedCandidateId)) ||
    null;
  const selectedSelection = selectedGraph
    ? (session.selectionByGroup[selectedGraph.candidate_group_id] ?? EMPTY_SELECTION)
    : EMPTY_SELECTION;
  const selectedValid = selectedGraph
    ? session.isSelectionValid(selectedGraph.candidate_group_id)
    : false;
  const selectedAllAssigned = selectedGraph
    ? selectedGraph.nodes.every((n) => session.assignedBlockIds.has(n.original_block_id))
    : false;
  const selectedCanGroupAll = selectedGraph
    ? session.canGroupAll(selectedGraph.candidate_group_id)
    : false;
  const selectedUnassignedCount = selectedGraph
    ? selectedGraph.nodes.filter((n) => !session.assignedBlockIds.has(n.original_block_id)).length
    : 0;

  // Create a group (or group-all) from the graph panel, then scroll its new card
  // into view.
  const handleCreateGroupForSelected = () => {
    if (!selectedGraph) return;
    const id = session.handleCreateGroup(selectedGraph.candidate_group_id);
    if (id) scrollGroupIntoView(id);
  };
  const handleGroupAllForSelected = () => {
    if (!selectedGraph) return;
    const id = session.handleGroupAll(selectedGraph.candidate_group_id);
    if (id) scrollGroupIntoView(id);
  };

  return {
    ...session,
    sortedDegrees,
    subjects,
    activeYearId,
    activeSubjectId,
    activeSubjectName,
    subjectGraphs,
    hasSubjects: subjects.length > 0,
    selectedCandidateId,
    groupIdsByCandidate,
    activeSubjectConfirmed,
    activeSubjectGroupViews,
    selectedGraph,
    selectedSelection,
    selectedValid,
    selectedAllAssigned,
    selectedCanGroupAll,
    selectedUnassignedCount,
    highlightedGroupId,
    groupsScrollRef,
    activeGroupColRef,
    registerGroupRef,
    handleRevealGroup,
    handleSelectSubject,
    handleConfirmActiveSubject,
    handleResetActiveSubject,
    handleUnconfirmActiveSubject,
    handleSelectCandidate,
    handleCreateGroupForSelected,
    handleGroupAllForSelected,
  };
}
