import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import type {
  DegreeOption,
  ParallelCandidate,
  SuccessResponse,
  YearOption,
} from "../../types/parallelClasses";

import { fetchJson, normalizeYears } from "../../types/parallelClasses";

export interface UseParallelClassesReturn {
  degrees: DegreeOption[];
  loadingDegrees: boolean;
  degreesError: string | null;
  selectedDegree: DegreeOption | null;
  handleDegreeClick: (degree: DegreeOption) => void;

  years: YearOption[];
  selectedYear: YearOption | null;
  handleYearClick: (year: YearOption) => void;

  parallelCandidates: ParallelCandidate[];
  isLoadingResults: boolean;
  candidatesError: string | null;
}

export function useParallelClasses(): UseParallelClassesReturn {
  const { projectId } = useParams<{ projectId: string }>();
  const projectIdNum = useMemo(() => Number(projectId), [projectId]);

  const [degrees, setDegrees] = useState<DegreeOption[]>([]);
  const [loadingDegrees, setLoadingDegrees] = useState(false);
  const [degreesError, setDegreesError] = useState<string | null>(null);
  const [selectedDegree, setSelectedDegree] = useState<DegreeOption | null>(null);

  const [years, setYears] = useState<YearOption[]>([]);
  const [selectedYear, setSelectedYear] = useState<YearOption | null>(null);
  const [resolvedYearId, setResolvedYearId] = useState<string | null>(null);
  const [loadingYearLookup, setLoadingYearLookup] = useState(false);

  const [parallelCandidates, setParallelCandidates] = useState<ParallelCandidate[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [candidatesError, setCandidatesError] = useState<string | null>(null);

  // ── Fetch degrees ────────────────────────────────────────────────────────

  useEffect(() => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    let cancelled = false;
    setLoadingDegrees(true);
    setDegreesError(null);

    fetchJson<SuccessResponse<{ degrees: DegreeOption[]; count: number }>>(
      `/api/projects/${projectIdNum}/degrees/with-parallel-candidates/`,
    )
      .then((res) => {
        if (!cancelled) setDegrees(res.data.degrees);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setDegreesError(err instanceof Error ? err.message : "Erro ao carregar cursos");
      })
      .finally(() => {
        if (!cancelled) setLoadingDegrees(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, projectIdNum]);

  // ── Resolve year ID ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!selectedDegree || !selectedYear || !projectId || Number.isNaN(projectIdNum)) return;
    let cancelled = false;
    setLoadingYearLookup(true);
    setResolvedYearId(null);
    setCandidatesError(null);
    setParallelCandidates([]);

    fetchJson<SuccessResponse<{ year_id: string }>>(
      `/api/projects/${projectIdNum}/degrees/${selectedDegree.id}/years/${selectedYear.year_number}`,
    )
      .then((res) => {
        if (!cancelled) setResolvedYearId(res.data.year_id);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setCandidatesError(err instanceof Error ? err.message : "Erro ao resolver ano");
      })
      .finally(() => {
        if (!cancelled) setLoadingYearLookup(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, projectIdNum, selectedDegree, selectedYear]);

  // ── Fetch parallel candidates ────────────────────────────────────────────

  useEffect(() => {
    if (
      !resolvedYearId ||
      !selectedDegree ||
      !selectedYear ||
      !projectId ||
      Number.isNaN(projectIdNum)
    )
      return;
    let cancelled = false;
    setLoadingCandidates(true);
    setCandidatesError(null);

    const params = new URLSearchParams({
      degree_id: selectedDegree.id,
      year_id: resolvedYearId,
    });

    fetchJson<SuccessResponse<ParallelCandidate[]>>(
      `/api/projects/${projectIdNum}/parallel-candidates?${params.toString()}`,
    )
      .then((res) => {
        if (!cancelled) setParallelCandidates(res.data);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setCandidatesError(err instanceof Error ? err.message : "Erro ao carregar sessões");
      })
      .finally(() => {
        if (!cancelled) setLoadingCandidates(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, projectIdNum, resolvedYearId, selectedDegree, selectedYear]);

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handleDegreeClick = (degree: DegreeOption) => {
    setSelectedDegree((prev) => {
      const next = prev?.id === degree.id ? null : degree;
      setYears(next ? normalizeYears(next.years) : []);
      setSelectedYear(null);
      setResolvedYearId(null);
      setParallelCandidates([]);
      setCandidatesError(null);
      return next;
    });
  };

  const handleYearClick = (year: YearOption) => {
    setSelectedYear((prev) => {
      const next = prev?.year_number === year.year_number ? null : year;
      setResolvedYearId(null);
      setParallelCandidates([]);
      setCandidatesError(null);
      return next;
    });
  };

  return {
    degrees,
    loadingDegrees,
    degreesError,
    selectedDegree,
    handleDegreeClick,
    years,
    selectedYear,
    handleYearClick,
    parallelCandidates,
    isLoadingResults: loadingYearLookup || loadingCandidates,
    candidatesError,
  };
}
