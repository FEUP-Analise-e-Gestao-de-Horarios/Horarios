import { useState } from "react";
import type { ReactNode } from "react";
import { AlertTriangle, ArrowLeftRight, Shuffle } from "lucide-react";
import { EmptyState, ExportSection } from "@/components/exporter/ExportSection";
import DependencyLinks from "@/components/exporter/DependencyLinks";
import ModificationChange from "@/components/exporter/ModificationChange";
import SessionAttributes from "@/components/exporter/SessionAttributes";
import type { ConflictLookup } from "@/utils/exporter/conflicts";
import { anchorId, normalizeId } from "@/utils/exporter/ids";
import type { DependencyLookup, ModificationPlanItem } from "@/utils/exporter/modificationPlan";
import {
  formatTime,
  formatWeekLabel,
  shouldShowWeekScope,
  WEEKDAY_LABELS,
} from "@/utils/exporter/formatters";
import { subjectTitleLabel, uniqueByLabel } from "@/utils/exporter/relations";
import type { ExportModificationStep, ExportSessionSnapshot } from "@/types/exporter";

function SubjectTitle({ subject }: { subject: ExportSessionSnapshot["subjects"][number] }) {
  const label = subject.acronym ?? subject.name;

  return (
    <span className="inline-flex items-baseline gap-1">
      <span>{label}</span>
      {subject.code && <span className="font-normal">({subject.code})</span>}
    </span>
  );
}

function sessionTitle(session: ExportSessionSnapshot): ReactNode {
  const subjects = uniqueByLabel(session.subjects, subjectTitleLabel);
  const classes = uniqueByLabel(session.classes, (classCode) => classCode).join(", ");

  if (!subjects.length && !classes) return "Sessão";

  return (
    <>
      {subjects.map((subject, index) => (
        <span key={subjectTitleLabel(subject)}>
          {index > 0 && ", "}
          <SubjectTitle subject={subject} />
        </span>
      ))}
      {subjects.length > 0 && classes && " · "}
      {classes}
    </>
  );
}

function changeTitle(session: ExportSessionSnapshot): ReactNode {
  return (
    <>
      {sessionTitle(session)} · {WEEKDAY_LABELS[session.weekday]} {formatTime(session.start_time)}
    </>
  );
}

function ChangeDetails({
  step,
  dependencies,
  dependencyLookup,
  conflictSessionIds,
  conflictLookup,
  highlightedAnchor,
  onDependencyClick,
  onConflictClick,
  getSessionOrder,
}: {
  step: ExportModificationStep;
  dependencies: string[];
  dependencyLookup: DependencyLookup;
  conflictSessionIds: Set<string>;
  conflictLookup: ConflictLookup;
  highlightedAnchor: string | null;
  onDependencyClick: (anchor: string) => void;
  onConflictClick: (anchor: string) => void;
  getSessionOrder: (sessionId: string) => number;
}) {
  const [isAttributesOpen, setIsAttributesOpen] = useState(false);
  const hasUnsolvedConflict = step.session_ids.some((sessionId) =>
    conflictSessionIds.has(normalizeId(sessionId)),
  );
  const isHighlighted = step.session_ids.some(
    (sessionId) => highlightedAnchor === anchorId(sessionId),
  );
  const conflictTarget = step.session_ids
    .map((sessionId) => conflictLookup[normalizeId(sessionId)])
    .find((target) => target !== undefined);

  return (
    <div
      className={`relative scroll-mt-4 overflow-hidden px-2 py-1 transition-colors duration-500 ease-out ${
        hasUnsolvedConflict ? "bg-red-100/90" : isHighlighted ? "bg-amber-50" : "bg-white"
      } ${isHighlighted ? "ring-2 ring-inset ring-amber-400" : ""}`}
    >
      {hasUnsolvedConflict && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-0 animate-pulse bg-red-300/70"
        />
      )}
      {isHighlighted && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-0 animate-pulse bg-amber-300/60"
        />
      )}
      <div className="relative z-10">
        {step.session_ids.map((sessionId) => (
          <span key={sessionId} id={anchorId(sessionId)} className="block scroll-mt-4" />
        ))}
        <details
          open={isAttributesOpen}
          onToggle={(event) => setIsAttributesOpen(event.currentTarget.open)}
        >
          <summary className="flex cursor-pointer list-none flex-wrap items-center gap-1.5 rounded px-1 py-0.5 marker:hidden hover:bg-white/50">
            <span className="min-w-0 break-words text-sm font-semibold text-[#08060d]">
              {changeTitle(step.session)}
            </span>
            {shouldShowWeekScope(step) && (
              <span className="inline-flex items-center rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-xs font-semibold text-amber-700">
                Apenas semanas {formatWeekLabel(step)}
              </span>
            )}
            <span className="ml-auto inline-flex flex-wrap items-center justify-end gap-1.5 whitespace-nowrap">
              {hasUnsolvedConflict && (
                <button
                  type="button"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    if (conflictTarget) onConflictClick(conflictTarget.anchor);
                  }}
                  className="inline-flex items-center gap-1 rounded border border-red-300 bg-red-50 px-1.5 py-0.5 text-xs font-semibold text-red-800 transition-colors hover:border-red-500 hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400 disabled:cursor-default disabled:opacity-80"
                  disabled={!conflictTarget}
                  aria-label={
                    conflictTarget
                      ? `Ver conflito por resolver: ${conflictTarget.label}`
                      : "Conflito por resolver"
                  }
                >
                  <AlertTriangle size={12} />
                  Esta alteração causa um conflito por resolver
                </button>
              )}
              {!hasUnsolvedConflict && (
                <DependencyLinks
                  dependencies={dependencies}
                  lookup={dependencyLookup}
                  currentOrder={Math.min(...step.session_ids.map(getSessionOrder))}
                  onDependencyClick={onDependencyClick}
                  className="mt-0"
                />
              )}
              <span className="text-xs font-semibold text-[#8c2d19]">
                {isAttributesOpen ? "Esconder detalhes" : "Ver detalhes"}
              </span>
            </span>
            {hasUnsolvedConflict && (
              <div className="flex basis-full justify-end">
                <DependencyLinks
                  dependencies={dependencies}
                  lookup={dependencyLookup}
                  currentOrder={Math.min(...step.session_ids.map(getSessionOrder))}
                  onDependencyClick={onDependencyClick}
                  className="mt-0"
                />
              </div>
            )}
          </summary>
          <div className="mt-1 px-1 pb-0.5">
            <SessionAttributes session={step.session} weekLabel={formatWeekLabel(step)} />
          </div>
        </details>
        <div className="mt-1 flex flex-wrap gap-1">
          {Object.entries(step.modifications).map(([name, change]) =>
            change ? (
              <ModificationChange key={name} name={name} change={change} stepType={step.type} />
            ) : null,
          )}
        </div>
      </div>
    </div>
  );
}

function ModificationStepCard({
  step,
  index,
  dependencyLookup,
  conflictSessionIds,
  conflictLookup,
  highlightedAnchor,
  onDependencyClick,
  onConflictClick,
  getSessionOrder,
}: {
  step: ExportModificationStep;
  index: number;
  dependencyLookup: DependencyLookup;
  conflictSessionIds: Set<string>;
  conflictLookup: ConflictLookup;
  highlightedAnchor: string | null;
  onDependencyClick: (anchor: string) => void;
  onConflictClick: (anchor: string) => void;
  getSessionOrder: (sessionId: string) => number;
}) {
  const Icon = step.type === "exchange" ? Shuffle : ArrowLeftRight;

  return (
    <article className="rounded-md border border-[#e5e4e7] overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-[#e5e4e7] bg-[#f9f7f4] px-3 py-1">
        <div className="flex items-center gap-1.5">
          <Icon size={14} className="text-[#8c2d19]" />
          <h3 className="text-sm font-bold text-[#08060d]">
            Passo {index + 1} · {step.type === "exchange" ? "Troca" : "Mover"}
          </h3>
        </div>
        <span className="text-xs font-semibold text-[#6b6375]">1 alteração</span>
      </div>
      <div className="divide-y divide-[#e5e4e7]">
        <ChangeDetails
          step={step}
          dependencies={step.dependencies}
          dependencyLookup={dependencyLookup}
          conflictSessionIds={conflictSessionIds}
          conflictLookup={conflictLookup}
          highlightedAnchor={highlightedAnchor}
          onDependencyClick={onDependencyClick}
          onConflictClick={onConflictClick}
          getSessionOrder={getSessionOrder}
        />
      </div>
    </article>
  );
}

function ExchangeClusterCard({
  steps,
  index,
  dependencyLookup,
  conflictSessionIds,
  conflictLookup,
  highlightedAnchor,
  onDependencyClick,
  onConflictClick,
  getSessionOrder,
}: {
  steps: ExportModificationStep[];
  index: number;
  dependencyLookup: DependencyLookup;
  conflictSessionIds: Set<string>;
  conflictLookup: ConflictLookup;
  highlightedAnchor: string | null;
  onDependencyClick: (anchor: string) => void;
  onConflictClick: (anchor: string) => void;
  getSessionOrder: (sessionId: string) => number;
}) {
  const clusterSessionIds = new Set(
    steps.flatMap((step) => step.session_ids.map((sessionId) => normalizeId(sessionId))),
  );

  return (
    <article className="rounded-md border border-[#e5e4e7] overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-[#e5e4e7] bg-[#f9f7f4] px-3 py-1">
        <div className="flex items-center gap-1.5">
          <Shuffle size={14} className="text-[#8c2d19]" />
          <h3 className="text-sm font-bold text-[#08060d]">Passo {index + 1} · Troca</h3>
        </div>
        <span className="text-xs font-semibold text-[#6b6375]">
          {steps.length} alterações agrupadas
        </span>
      </div>
      <div className="divide-y divide-[#e5e4e7]">
        {steps.map((step) => {
          const externalDependencies = step.dependencies.filter(
            (dependency) => !clusterSessionIds.has(normalizeId(String(dependency))),
          );

          return (
            <ChangeDetails
              key={step.session_ids.join("-")}
              step={step}
              dependencies={externalDependencies}
              dependencyLookup={dependencyLookup}
              conflictSessionIds={conflictSessionIds}
              conflictLookup={conflictLookup}
              highlightedAnchor={highlightedAnchor}
              onDependencyClick={onDependencyClick}
              onConflictClick={onConflictClick}
              getSessionOrder={getSessionOrder}
            />
          );
        })}
      </div>
    </article>
  );
}

export default function ModificationPlanSection({
  items,
  dependencyLookup,
  conflictSessionIds,
  conflictLookup,
  highlightedAnchor,
  onDependencyClick,
  onConflictClick,
  getSessionOrder,
}: {
  items: ModificationPlanItem[];
  dependencyLookup: DependencyLookup;
  conflictSessionIds: Set<string>;
  conflictLookup: ConflictLookup;
  highlightedAnchor: string | null;
  onDependencyClick: (anchor: string) => void;
  onConflictClick: (anchor: string) => void;
  getSessionOrder: (sessionId: string) => number;
}) {
  return (
    <ExportSection title="Plano de Modificações" defaultOpen>
      {items.length ? (
        <div className="grid gap-2 p-3">
          {items.map((item, index) =>
            item.kind === "exchangeCluster" ? (
              <ExchangeClusterCard
                key={item.steps.flatMap((step) => step.session_ids).join("-")}
                steps={item.steps}
                index={index}
                dependencyLookup={dependencyLookup}
                conflictSessionIds={conflictSessionIds}
                conflictLookup={conflictLookup}
                highlightedAnchor={highlightedAnchor}
                onDependencyClick={onDependencyClick}
                onConflictClick={onConflictClick}
                getSessionOrder={getSessionOrder}
              />
            ) : (
              <ModificationStepCard
                key={item.step.session_ids.join("-")}
                step={item.step}
                index={index}
                dependencyLookup={dependencyLookup}
                conflictSessionIds={conflictSessionIds}
                conflictLookup={conflictLookup}
                highlightedAnchor={highlightedAnchor}
                onDependencyClick={onDependencyClick}
                onConflictClick={onConflictClick}
                getSessionOrder={getSessionOrder}
              />
            ),
          )}
        </div>
      ) : (
        <EmptyState>Sem modificações.</EmptyState>
      )}
    </ExportSection>
  );
}
