import { useMemo } from "react";
import { useParams } from "react-router-dom";
import AddedRemovedSessions from "@/components/exporter/added-removed/AddedRemovedSessions";
import ExporterConflictsSection from "@/components/exporter/conflicts/ExporterConflictsSection";
import ExporterStats from "@/components/exporter/summary/ExporterStats";
import ModificationPlanSection from "@/components/exporter/modification-plan/ModificationPlanSection";
import { ExportSection } from "@/components/exporter/ExportSection";
import { useSetExportChecklistItem } from "@/api/hooks/useDashboard";
import useExporterNavigationState from "@/api/hooks/useExporterNavigationState";
import { buildConflictLookup, buildConflictSessionIds } from "@/utils/exporter/conflicts";
import { normalizeId } from "@/utils/exporter/ids";
import {
  buildDependencyLookup,
  buildModificationPlanItems,
} from "@/utils/exporter/modificationPlan";
import type { ProjectExportPayload } from "@/types/exporter";

export default function ExportResults({ data }: { data: ProjectExportPayload }) {
  const { projectId = "" } = useParams<{ projectId: string }>();
  const navigationState = useExporterNavigationState(projectId);
  const checklistMutation = useSetExportChecklistItem(projectId);
  const checkedItemKeys = useMemo(
    () => new Set(data.checked_item_keys ?? []),
    [data.checked_item_keys],
  );
  const modificationPlanItems = useMemo(
    () => buildModificationPlanItems(data.modification_steps),
    [data.modification_steps],
  );
  const dependencyLookup = useMemo(
    () => buildDependencyLookup(modificationPlanItems),
    [modificationPlanItems],
  );
  const conflictSessionIds = useMemo(() => buildConflictSessionIds(data), [data]);
  const conflictLookup = useMemo(() => buildConflictLookup(data), [data]);
  const totalConflicts =
    data.rooms_conflicts.length + data.teacher_conflicts.length + data.classes_conflicts.length;

  function getSessionOrder(sessionId: string) {
    return dependencyLookup[normalizeId(sessionId)]?.order ?? Number.MAX_SAFE_INTEGER;
  }

  return (
    <div className="space-y-3">
      <ExporterStats data={data} totalConflicts={totalConflicts} />

      <ExporterConflictsSection
        data={data}
        projectId={projectId}
        totalConflicts={totalConflicts}
        highlightedAnchor={navigationState.highlightedConflictAnchor}
        isOpen={navigationState.isConflictsOpen}
        onOpenChange={navigationState.handleConflictsOpenChange}
        onCardClick={navigationState.handleConflictCardClick}
      />

      <ExportSection title="Aulas Adicionadas e removidas">
        <AddedRemovedSessions
          data={data.added_removed_sessions}
          projectId={projectId}
          checkedItemKeys={checkedItemKeys}
          onCheckedChange={(itemKey, checked) => checklistMutation.mutate({ itemKey, checked })}
        />
      </ExportSection>

      <ModificationPlanSection
        items={modificationPlanItems}
        dependencyLookup={dependencyLookup}
        conflictSessionIds={conflictSessionIds}
        conflictLookup={conflictLookup}
        highlightedAnchor={navigationState.highlightedAnchor}
        onDependencyClick={navigationState.handleDependencyClick}
        onConflictClick={navigationState.handleConflictReferenceClick}
        getSessionOrder={getSessionOrder}
        checkedItemKeys={checkedItemKeys}
        onCheckedChange={(itemKey, checked) => checklistMutation.mutate({ itemKey, checked })}
      />
    </div>
  );
}
