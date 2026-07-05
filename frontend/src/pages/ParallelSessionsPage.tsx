import { useMemo, useState } from "react";
import { useParallelSessions } from "@/api/hooks/parallel/sessions";
import { useGroupReveal } from "@/components/parallel/useGroupReveal";
import { DAY_ORDER, type ParallelCandidateGraph } from "@/types/parallelSessions";
import { EMPTY_SELECTION, graphStartTime } from "@/components/parallel/parallelDisplay";
import ParallelHeader from "@/components/parallel/ParallelHeader";
import SubjectSelectors from "@/components/parallel/SubjectSelectors";
import CandidateList from "@/components/parallel/CandidateList";
import GraphPanel from "@/components/parallel/GraphPanel";
import SelectedGroupsPanel from "@/components/parallel/SelectedGroupsPanel";
import ResetModal from "@/components/parallel/ResetModal";
import FinishModal from "@/components/parallel/FinishModal";
import StaleConfirmModal from "@/components/parallel/StaleConfirmModal";

export default function ParallelClassesPage() {
  // Per-subject memory of which candidate's graph is open, mirroring how the
  // year is remembered per degree and the subject per year. Keeps a graph
  // selected only while its subject is active, and restores it on return.
  const [selectedCandidateBySubject, setSelectedCandidateBySubject] = useState<
    Record<string, string | null>
  >({});
  // Per-year memory of the chosen subject.
  const [selectedSubjectByYear, setSelectedSubjectByYear] = useState<Record<string, string>>({});

  const {
    degrees,
    loadingDegrees,
    degreesError,
    selectedDegree,
    selectedYearIds,
    yearsWithCandidates,
    loadingCandidates,
    candidatesError,
    visibleGraphs,
    assignedBlockIds,
    selectionByGroup,
    isSelectionValid,
    canGroupAll,
    groupViewsBySubject,
    saving,
    showResetModal,
    setShowResetModal,
    confirmedSubjectIds,
    confirmedYearIds,
    confirmedDegreeIds,
    confirmSubject,
    unconfirmSubject,
    unconfirmedByDegree,
    showFinishModal,
    setShowFinishModal,
    staleConfirmScope,
    setStaleConfirmScope,
    handleFinish,
    finishAndConfirmAll,
    finishContinue,
    finishLater,
    handleDegreeClick,
    handleYearSelect,
    handleToggleNode,
    handleCreateGroup,
    handleGroupAll,
    handleRemoveGroup,
    handleRemoveGroups,
    handleBack,
    handleNavigateHome,
    handleReset,
    confirmReset,
  } = useParallelSessions();

  // Group the visible candidate components by subject, sorted for display.
  const graphsBySubject = useMemo(() => {
    const map = new Map<string, ParallelCandidateGraph[]>();
    for (const g of visibleGraphs) {
      const key = g.subject.name;
      const list = map.get(key);
      if (list) list.push(g);
      else map.set(key, [g]);
    }
    for (const list of map.values()) {
      list.sort(
        (a, b) =>
          (DAY_ORDER[a.weekday] ?? 99) - (DAY_ORDER[b.weekday] ?? 99) ||
          graphStartTime(a) - graphStartTime(b),
      );
    }
    return map;
  }, [visibleGraphs]);

  // Degrees for the left-column selector, alphabetically sorted by acronym.
  const sortedDegrees = useMemo(
    () => [...degrees].sort((a, b) => a.acronym.localeCompare(b.acronym)),
    [degrees],
  );

  // Subjects available in the left-column selector, alphabetically sorted.
  const subjectNames = useMemo(
    () => [...graphsBySubject.keys()].sort((a, b) => a.localeCompare(b)),
    [graphsBySubject],
  );

  // Full subject name -> acronym, for the compact selector pills.
  const subjectAcronyms = useMemo(() => {
    const map = new Map<string, string>();
    for (const g of visibleGraphs) map.set(g.subject.name, g.subject.acronym);
    return map;
  }, [visibleGraphs]);

  // Full subject name -> subject id, to key confirmation off the selector pills.
  const subjectIdByName = useMemo(() => {
    const map = new Map<string, string>();
    for (const g of visibleGraphs) map.set(g.subject.name, g.subject.id);
    return map;
  }, [visibleGraphs]);

  // The single selected year driving the candidate list.
  const activeYearId = yearsWithCandidates.find((y) => selectedYearIds.has(y.id))?.id ?? null;

  // Resolve the effective subject: the one remembered for the active year when it
  // still exists, else the first available (e.g. after a degree/year change).
  const rememberedSubject = activeYearId ? selectedSubjectByYear[activeYearId] : undefined;
  const activeSubject =
    rememberedSubject && subjectNames.includes(rememberedSubject)
      ? rememberedSubject
      : (subjectNames[0] ?? null);

  const subjectGraphs = activeSubject ? (graphsBySubject.get(activeSubject) ?? []) : [];

  // The open candidate, remembered per subject and constrained to it so a graph
  // only stays selected while its subject is active.
  const selectedCandidateId = activeSubject
    ? (selectedCandidateBySubject[activeSubject] ?? null)
    : null;

  const {
    groupsScrollRef,
    activeGroupColRef,
    highlightedGroupId,
    registerGroupRef,
    revealGroup,
    scrollGroupIntoView,
    handleRevealGroup,
  } = useGroupReveal(activeSubject, groupViewsBySubject);

  // Candidate id -> ids of the groups already carved out of it.
  const groupIdsByCandidate = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const items of groupViewsBySubject.values())
      for (const view of items) {
        const arr = map.get(view.group.candidateGroupId);
        if (arr) arr.push(view.group.id);
        else map.set(view.group.candidateGroupId, [view.group.id]);
      }
    return map;
  }, [groupViewsBySubject]);

  // Remember the chosen subject for the active year.
  const handleSelectSubject = (name: string) => {
    if (activeYearId) setSelectedSubjectByYear((prev) => ({ ...prev, [activeYearId]: name }));
  };

  const activeSubjectId = activeSubject ? (subjectIdByName.get(activeSubject) ?? null) : null;
  const activeSubjectConfirmed = activeSubjectId ? confirmedSubjectIds.has(activeSubjectId) : false;
  // The groups already created for the active subject (in the current year).
  const activeSubjectGroupViews = activeSubject
    ? (groupViewsBySubject.get(activeSubject) ?? [])
    : [];

  // Confirm the active subject, then jump the selector to the next subject that
  // is still unconfirmed (searching forward from the current one, then wrapping).
  // If the confirm is rejected, the optimistic jump is reverted.
  const handleConfirmActiveSubject = () => {
    if (!activeSubject || !activeSubjectId) return;
    const prevSubject = activeSubject;
    const yearId = activeYearId;
    const confirmedNow = new Set(confirmedSubjectIds).add(activeSubjectId);
    const idx = subjectNames.indexOf(activeSubject);
    const ordered = [...subjectNames.slice(idx + 1), ...subjectNames.slice(0, idx)];
    const next = ordered.find((name) => {
      const id = subjectIdByName.get(name);
      return id && !confirmedNow.has(id);
    });
    void confirmSubject(activeSubjectId).then((ok) => {
      // On failure undo the jump, but only if the user hasn't since moved on.
      if (!ok && next && yearId) {
        setSelectedSubjectByYear((prev) =>
          prev[yearId] === next ? { ...prev, [yearId]: prevSubject } : prev,
        );
      }
    });
    if (next && yearId) {
      setSelectedSubjectByYear((prev) => ({ ...prev, [yearId]: next }));
    }
  };

  // Repor: drop every group already formed for the active subject in one batch,
  // so the whole reset triggers a single cache invalidation instead of one per
  // group.
  const handleResetActiveSubject = () => {
    handleRemoveGroups(activeSubjectGroupViews.map((view) => view.group.id));
  };

  // Undo confirmation (fired by clicking the confirmed button, which reddens on
  // hover to signal the destructive action).
  const handleUnconfirmActiveSubject = () => {
    if (activeSubjectId) unconfirmSubject(activeSubjectId);
  };

  // Open/close a candidate's graph, remembered per subject. Opening one that
  // already has exactly one group also jumps to that group.
  const handleSelectCandidate = (candidateId: string) => {
    if (!activeSubject) return;
    const closing = selectedCandidateBySubject[activeSubject] === candidateId;
    setSelectedCandidateBySubject((prev) => ({
      ...prev,
      [activeSubject]: closing ? null : candidateId,
    }));
    if (!closing) {
      const ids = groupIdsByCandidate.get(candidateId);
      if (ids && ids.length === 1) requestAnimationFrame(() => revealGroup(ids[0]!));
    }
  };

  // The candidate currently driving the graph panel, resolved within the active
  // subject so it collapses when its subject (or year) is no longer selected.
  const selectedGraph =
    (selectedCandidateId &&
      subjectGraphs.find((g) => g.candidate_group_id === selectedCandidateId)) ||
    null;
  const selectedSelection = selectedGraph
    ? (selectionByGroup[selectedGraph.candidate_group_id] ?? EMPTY_SELECTION)
    : EMPTY_SELECTION;
  const selectedValid = selectedGraph ? isSelectionValid(selectedGraph.candidate_group_id) : false;
  const selectedAllAssigned = selectedGraph
    ? selectedGraph.nodes.every((n) => assignedBlockIds.has(n.original_block_id))
    : false;
  const selectedCanGroupAll = selectedGraph ? canGroupAll(selectedGraph.candidate_group_id) : false;
  const selectedUnassignedCount = selectedGraph
    ? selectedGraph.nodes.filter((n) => !assignedBlockIds.has(n.original_block_id)).length
    : 0;

  // Create a group (or group-all) from the graph panel, then scroll its new card
  // into view once it has mounted.
  const handleCreateGroupForSelected = () => {
    if (!selectedGraph) return;
    const id = handleCreateGroup(selectedGraph.candidate_group_id);
    if (id) requestAnimationFrame(() => scrollGroupIntoView(id));
  };
  const handleGroupAllForSelected = () => {
    if (!selectedGraph) return;
    const id = handleGroupAll(selectedGraph.candidate_group_id);
    if (id) requestAnimationFrame(() => scrollGroupIntoView(id));
  };

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <ParallelHeader
        saving={saving}
        onNavigateHome={handleNavigateHome}
        onBack={handleBack}
        onReset={handleReset}
        onFinish={handleFinish}
      />

      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-7xl mx-auto px-6 py-6 flex gap-6">
          {/* Left column: degree/year/subject selectors + candidates */}
          <div className="w-[360px] shrink-0 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-3 shrink-0">
              <h2 className="font-bold text-[#333] text-base">Candidatos a paralelas</h2>
            </div>

            <SubjectSelectors
              degreesError={degreesError}
              sortedDegrees={sortedDegrees}
              loadingDegrees={loadingDegrees}
              selectedDegree={selectedDegree}
              confirmedDegreeIds={confirmedDegreeIds}
              onDegreeClick={handleDegreeClick}
              yearsWithCandidates={yearsWithCandidates}
              activeYearId={activeYearId}
              confirmedYearIds={confirmedYearIds}
              onYearSelect={handleYearSelect}
              subjectNames={subjectNames}
              activeSubject={activeSubject}
              subjectIdByName={subjectIdByName}
              subjectAcronyms={subjectAcronyms}
              confirmedSubjectIds={confirmedSubjectIds}
              onSelectSubject={handleSelectSubject}
            />

            <CandidateList
              loadingCandidates={loadingCandidates}
              candidatesError={candidatesError}
              hasSubjects={graphsBySubject.size > 0}
              hasSelectedDegree={!!selectedDegree}
              activeSubject={activeSubject}
              activeSubjectGroupViews={activeSubjectGroupViews}
              activeSubjectConfirmed={activeSubjectConfirmed}
              saving={saving}
              onResetActiveSubject={handleResetActiveSubject}
              onUnconfirmActiveSubject={handleUnconfirmActiveSubject}
              onConfirmActiveSubject={handleConfirmActiveSubject}
              subjectGraphs={subjectGraphs}
              selectionByGroup={selectionByGroup}
              assignedBlockIds={assignedBlockIds}
              groupIdsByCandidate={groupIdsByCandidate}
              selectedCandidateId={selectedCandidateId}
              onSelectCandidate={handleSelectCandidate}
            />
          </div>

          {/* Right column: graph (top) + selected groups (bottom) */}
          <div className="flex-1 min-w-0 flex flex-col gap-4 min-h-0">
            <GraphPanel
              selectedGraph={selectedGraph}
              selectedSelection={selectedSelection}
              selectedValid={selectedValid}
              selectedAllAssigned={selectedAllAssigned}
              selectedCanGroupAll={selectedCanGroupAll}
              selectedUnassignedCount={selectedUnassignedCount}
              assignedBlockIds={assignedBlockIds}
              loadingCandidates={loadingCandidates}
              onCreateGroup={handleCreateGroupForSelected}
              onGroupAll={handleGroupAllForSelected}
              onToggleNode={(blockId) =>
                selectedGraph && handleToggleNode(selectedGraph.candidate_group_id, blockId)
              }
              onTapAssigned={handleRevealGroup}
            />

            <SelectedGroupsPanel
              loadingCandidates={loadingCandidates}
              groupViewsBySubject={groupViewsBySubject}
              activeSubject={activeSubject}
              highlightedGroupId={highlightedGroupId}
              onRemoveGroup={handleRemoveGroup}
              scrollRef={groupsScrollRef}
              activeColRef={activeGroupColRef}
              registerGroupRef={registerGroupRef}
            />
          </div>
        </div>
      </div>

      {showResetModal && (
        <ResetModal onConfirm={confirmReset} onCancel={() => setShowResetModal(false)} />
      )}

      {showFinishModal && (
        <FinishModal
          unconfirmedByDegree={unconfirmedByDegree}
          onConfirmAll={finishAndConfirmAll}
          onContinue={finishContinue}
          onContinueLater={finishLater}
          onCancel={() => setShowFinishModal(false)}
        />
      )}

      {staleConfirmScope && (
        <StaleConfirmModal scope={staleConfirmScope} onDismiss={() => setStaleConfirmScope(null)} />
      )}
    </div>
  );
}
