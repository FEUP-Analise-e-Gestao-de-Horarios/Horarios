import type { ExportModificationStep } from "@/types/exporter";
import { anchorId, normalizeId } from "@/utils/exporter/ids";

export interface DependencyTarget {
  anchor: string;
  label: string;
  order: number;
}

export type DependencyLookup = Record<string, DependencyTarget>;

export type ModificationPlanItem =
  | { kind: "single"; step: ExportModificationStep }
  | { kind: "exchangeCluster"; steps: ExportModificationStep[] };

export function modificationPlanItemSteps(item: ModificationPlanItem): ExportModificationStep[] {
  return item.kind === "exchangeCluster" ? item.steps : [item.step];
}

export function buildDependencyLookup(items: ModificationPlanItem[]): DependencyLookup {
  const lookup: DependencyLookup = {};

  for (const [itemIndex, item] of items.entries()) {
    const stepNumber = itemIndex + 1;
    for (const step of modificationPlanItemSteps(item)) {
      for (const sessionId of step.session_ids) {
        lookup[normalizeId(sessionId)] = {
          anchor: anchorId(sessionId),
          label: `Passo ${stepNumber}`,
          order: itemIndex,
        };
      }
    }
  }

  return lookup;
}

export function buildModificationPlanItems(
  steps: ExportModificationStep[],
): ModificationPlanItem[] {
  const exchangeIndexes = steps
    .map((step, index) => ({ step, index }))
    .filter(({ step }) => step.type === "exchange");
  const exchangeIndexBySessionId = new Map<string, number>();

  for (const { step, index } of exchangeIndexes) {
    for (const sessionId of step.session_ids) {
      exchangeIndexBySessionId.set(normalizeId(sessionId), index);
    }
  }

  const parent = new Map<number, number>();
  for (const { index } of exchangeIndexes) {
    parent.set(index, index);
  }

  function find(index: number): number {
    const current = parent.get(index);
    if (current === undefined || current === index) return index;

    const root = find(current);
    parent.set(index, root);
    return root;
  }

  function union(left: number, right: number) {
    const leftRoot = find(left);
    const rightRoot = find(right);
    if (leftRoot !== rightRoot) parent.set(rightRoot, leftRoot);
  }

  for (const { step, index } of exchangeIndexes) {
    for (const dependency of step.dependencies) {
      const dependencyIndex = exchangeIndexBySessionId.get(normalizeId(String(dependency)));
      if (dependencyIndex !== undefined) union(index, dependencyIndex);
    }
  }

  const groupsByRoot = new Map<number, number[]>();
  for (const { index } of exchangeIndexes) {
    const root = find(index);
    groupsByRoot.set(root, [...(groupsByRoot.get(root) ?? []), index]);
  }

  const clusteredIndexes = new Set<number>();
  const clusterByFirstIndex = new Map<number, number[]>();
  for (const indexes of groupsByRoot.values()) {
    if (indexes.length < 2) continue;

    const sortedIndexes = indexes.toSorted((left, right) => left - right);
    const firstIndex = sortedIndexes[0];
    if (firstIndex === undefined) continue;

    for (const index of sortedIndexes) clusteredIndexes.add(index);
    clusterByFirstIndex.set(firstIndex, sortedIndexes);
  }

  return steps.flatMap((step, index): ModificationPlanItem[] => {
    const clusterIndexes = clusterByFirstIndex.get(index);
    if (clusterIndexes) {
      const clusterSteps = clusterIndexes
        .map((stepIndex) => steps[stepIndex])
        .filter((clusterStep): clusterStep is ExportModificationStep => clusterStep !== undefined);

      return [{ kind: "exchangeCluster", steps: clusterSteps }];
    }

    if (clusteredIndexes.has(index)) return [];
    return [{ kind: "single", step }];
  });
}
