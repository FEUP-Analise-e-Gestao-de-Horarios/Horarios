import { useParallelSessionsView } from "@/components/parallel/useParallelSessionsView";
import ParallelHeader from "@/components/parallel/ParallelHeader";
import SubjectSelectors from "@/components/parallel/SubjectSelectors";
import CandidateList from "@/components/parallel/CandidateList";
import GraphPanel from "@/components/parallel/GraphPanel";
import SelectedGroupsPanel from "@/components/parallel/SelectedGroupsPanel";
import ResetModal from "@/components/parallel/ResetModal";
import FinishModal from "@/components/parallel/FinishModal";
import StaleConfirmModal from "@/components/parallel/StaleConfirmModal";

export default function ParallelSessionsPage() {
  const {
    saving,
    handleNavigateHome,
    handleNavigateDashboard,
    handleBack,
    handleReset,
    handleFinish,
    candidatesError,
    sortedDegrees,
    loadingCandidates,
    selectedDegree,
    confirmedDegreeIds,
    handleDegreeClick,
    yearsWithCandidates,
    activeYearId,
    confirmedYearIds,
    handleYearSelect,
    subjects,
    activeSubjectId,
    confirmedSubjectIds,
    handleSelectSubject,
    hasSubjects,
    activeSubjectName,
    activeSubjectGroupViews,
    activeSubjectConfirmed,
    handleResetActiveSubject,
    handleUnconfirmActiveSubject,
    handleConfirmActiveSubject,
    subjectGraphs,
    selectionByGroup,
    assignedBlockIds,
    groupIdsByCandidate,
    selectedCandidateId,
    handleSelectCandidate,
    selectedGraph,
    selectedSelection,
    selectedValid,
    selectedAllAssigned,
    selectedCanGroupAll,
    selectedUnassignedCount,
    handleToggleNode,
    handleCreateGroupForSelected,
    handleGroupAllForSelected,
    handleRevealGroup,
    groupViewsBySubject,
    highlightedGroupId,
    handleRemoveGroup,
    groupsScrollRef,
    activeGroupColRef,
    registerGroupRef,
    showResetModal,
    setShowResetModal,
    confirmReset,
    showFinishModal,
    setShowFinishModal,
    unconfirmedByDegree,
    finishAndConfirmAll,
    finishContinue,
    finishLater,
    staleConfirmScope,
    setStaleConfirmScope,
  } = useParallelSessionsView();

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <ParallelHeader
        saving={saving}
        onNavigateHome={handleNavigateHome}
        onNavigateDashboard={handleNavigateDashboard}
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
              degreesError={candidatesError}
              sortedDegrees={sortedDegrees}
              loadingDegrees={loadingCandidates}
              selectedDegree={selectedDegree}
              confirmedDegreeIds={confirmedDegreeIds}
              onDegreeClick={handleDegreeClick}
              yearsWithCandidates={yearsWithCandidates}
              activeYearId={activeYearId}
              confirmedYearIds={confirmedYearIds}
              onYearSelect={handleYearSelect}
              subjects={subjects}
              activeSubjectId={activeSubjectId}
              confirmedSubjectIds={confirmedSubjectIds}
              onSelectSubject={handleSelectSubject}
            />

            <CandidateList
              loadingCandidates={loadingCandidates}
              candidatesError={candidatesError}
              hasSubjects={hasSubjects}
              hasSelectedDegree={!!selectedDegree}
              activeSubjectName={activeSubjectName}
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
              activeSubjectId={activeSubjectId}
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
