import { useEffect, useMemo, useRef, useState } from "react";
import {
  type DegreeOption,
  type ParallelCandidateGraph,
  type UUID,
  type YearOption,
} from "@/types/parallelSessions";

/** Owns the degree/year filter: derives the degree and year rows from the
 * candidate payload, auto-selects sensible defaults (restoring the last view
 * from sessionStorage), and narrows the graphs to the current filter. */
export function useParallelFilters(
  projectId: string | undefined,
  graphs: ParallelCandidateGraph[],
) {
  const [restoredState] = useState<{ degreeId: string; yearIds: string[] } | null>(() => {
    const raw = sessionStorage.getItem(`parallelSessions-${projectId ?? ""}`);
    if (!raw) return null;
    sessionStorage.removeItem(`parallelSessions-${projectId ?? ""}`);
    try {
      return JSON.parse(raw) as { degreeId: string; yearIds: string[] };
    } catch {
      return null;
    }
  });

  const [selectedDegree, setSelectedDegree] = useState<DegreeOption | null>(null);
  const [selectedYearIds, setSelectedYearIds] = useState<Set<UUID>>(new Set());
  // Remembers the last year picked per degree, so returning to a degree restores it.
  const yearByDegree = useRef<Record<string, UUID>>({});

  // -- Degrees derived from the candidate payload -----------------------
  const degrees = useMemo<DegreeOption[]>(() => {
    const map = new Map<UUID, DegreeOption>();
    for (const g of graphs) {
      for (const y of g.subject.years) {
        if (!map.has(y.degree.id)) {
          map.set(y.degree.id, { id: y.degree.id, name: y.degree.name, acronym: y.degree.acronym });
        }
      }
    }
    return [...map.values()].sort((a, b) => a.acronym.localeCompare(b.acronym));
  }, [graphs]);

  // Auto-select a degree once they are known (restored, else L.EIC, else first).
  useEffect(() => {
    if (selectedDegree || degrees.length === 0) return;
    const restored = restoredState?.degreeId
      ? degrees.find((d) => d.id === restoredState.degreeId)
      : undefined;
    const leic = degrees.find((d) => d.acronym.toUpperCase() === "L.EIC");
    const fallback = restored ?? leic ?? degrees[0];
    if (!fallback) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelectedDegree(fallback);
  }, [degrees, selectedDegree, restoredState]);

  // Graphs that belong to the selected degree.
  const degreeGraphs = useMemo(
    () =>
      selectedDegree
        ? graphs.filter((g) => g.subject.years.some((y) => y.degree.id === selectedDegree.id))
        : [],
    [graphs, selectedDegree],
  );

  // Year rows of the selected degree, read straight off the candidate payload:
  // every `subject.years` entry is a year the group is taught in, carrying its
  // number for the label and ordering. No separate per-degree request needed.
  const yearsWithCandidates = useMemo<YearOption[]>(() => {
    if (!selectedDegree) return [];
    const byId = new Map<UUID, YearOption>();
    for (const g of degreeGraphs) {
      for (const y of g.subject.years) {
        if (y.degree.id === selectedDegree.id && !byId.has(y.id)) {
          byId.set(y.id, { id: y.id, number: y.number });
        }
      }
    }
    return [...byId.values()].sort((a, b) => a.number - b.number);
  }, [degreeGraphs, selectedDegree]);

  // Default year selection to all years with candidates (or the restored set).
  const yearsKey = useMemo(
    () => yearsWithCandidates.map((y) => y.id).join(","),
    [yearsWithCandidates],
  );
  useEffect(() => {
    const firstYear = yearsWithCandidates[0];
    if (!firstYear) return;
    const allowed = new Set(yearsWithCandidates.map((y) => y.id));
    // Prefer the year last picked for this degree, then a restored one, else the
    // first — so returning to a degree restores the year you were on.
    const remembered = selectedDegree ? yearByDegree.current[selectedDegree.id] : undefined;
    const restored =
      restoredState?.degreeId === selectedDegree?.id ? restoredState?.yearIds : undefined;
    const restoredYear = restored?.find((id) => allowed.has(id));
    const pick =
      (remembered && allowed.has(remembered) ? remembered : undefined) ??
      restoredYear ??
      firstYear.id;
    setSelectedYearIds(new Set([pick]));
    // Re-run when the set of candidate years changes (e.g. degree switch).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [yearsKey]);

  const selectedYearIdSet = selectedYearIds;

  // Visible graphs: belong to the degree and touch a selected year.
  const visibleGraphs = useMemo(() => {
    if (selectedYearIdSet.size === 0) return degreeGraphs;
    return degreeGraphs.filter((g) =>
      g.nodes.some((node) => node.classes.some((cls) => selectedYearIdSet.has(cls.year_id))),
    );
  }, [degreeGraphs, selectedYearIdSet]);

  // Selecting a degree keeps the selector on it (no-op re-select is idempotent);
  // clearing the in-progress node selection is composed by the caller.
  const handleDegreeClick = (degree: DegreeOption) => {
    setSelectedDegree((prev) => (prev?.id === degree.id ? prev : degree));
  };

  // Single-year selection for the pill selector: replace the whole set and
  // remember it for the current degree.
  const handleYearSelect = (yearId: UUID) => {
    if (selectedDegree) yearByDegree.current[selectedDegree.id] = yearId;
    setSelectedYearIds(new Set([yearId]));
  };

  // Remember the current degree/year so returning to the page restores it.
  const rememberView = () => {
    if (!projectId) return;
    sessionStorage.setItem(
      `parallelSessions-${projectId}`,
      JSON.stringify({ degreeId: selectedDegree?.id, yearIds: [...selectedYearIds] }),
    );
  };

  return {
    selectedDegree,
    selectedYearIds,
    degrees,
    yearsWithCandidates,
    visibleGraphs,
    handleDegreeClick,
    handleYearSelect,
    rememberView,
  };
}
