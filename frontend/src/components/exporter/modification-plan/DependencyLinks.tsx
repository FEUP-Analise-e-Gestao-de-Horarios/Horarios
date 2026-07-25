import type { DependencyLookup } from "@/utils/exporter/modificationPlan";
import { normalizeId, shortId } from "@/utils/exporter/ids";

export default function DependencyLinks({
  dependencies,
  dependencyConflicts,
  lookup,
  currentOrder,
  onDependencyClick,
  label = "Causa um conflito resolvido pelo",
  className = "mt-2",
}: {
  dependencies: string[];
  dependencyConflicts?: Record<string, string[]>;
  lookup: DependencyLookup;
  currentOrder: number;
  onDependencyClick: (anchor: string) => void;
  label?: string;
  className?: string;
}) {
  const flaggedDependencies = dependencies.filter((dependency) => {
    const target = lookup[normalizeId(String(dependency))];
    return target ? target.order > currentOrder : false;
  });

  if (!flaggedDependencies.length) return null;

  const normalizedDependencyConflicts = Object.fromEntries(
    Object.entries(dependencyConflicts ?? {}).map(([dependency, kinds]) => [
      normalizeId(dependency),
      kinds,
    ]),
  );
  const conflictKinds = Array.from(
    new Set(
      flaggedDependencies.flatMap(
        (dependency) => normalizedDependencyConflicts[normalizeId(String(dependency))] ?? [],
      ),
    ),
  );
  const conflictLabel = conflictKinds.length
    ? `Conflito de ${conflictKinds
        .map((kind) => (kind === "room" ? "sala" : kind === "teacher" ? "docente" : "turma"))
        .join(", ")}`
    : label;

  return (
    <div className={`inline-flex flex-wrap items-center gap-1 text-xs ${className}`}>
      <span className="font-semibold text-red-700">{conflictLabel} resolvido pelo</span>
      {flaggedDependencies.map((dependency) => {
        const target = lookup[normalizeId(String(dependency))];
        if (!target) {
          return (
            <span
              key={dependency}
              className="rounded border border-red-200 bg-red-50 px-1 py-0.5 text-red-700"
            >
              {shortId(String(dependency))}
            </span>
          );
        }

        return (
          <a
            key={dependency}
            href={`#${target.anchor}`}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              onDependencyClick(target.anchor);
            }}
            className="rounded border border-red-200 bg-red-50 px-1 py-0.5 font-medium text-red-700 hover:border-red-400 hover:bg-red-100"
          >
            {target.label}
          </a>
        );
      })}
    </div>
  );
}
