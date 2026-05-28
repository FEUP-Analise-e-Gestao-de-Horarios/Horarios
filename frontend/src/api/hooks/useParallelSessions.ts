import { type Dispatch, type SetStateAction, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { ApiError, type ApiRequestError } from "@/types/api";
import { ROUTES } from "@/routes";
import { queryKeys } from "@/api/queryKeys";
import {
  DAY_ORDER,
  type BlockMeta,
  type DegreeOption,
  type DisplayCandidate,
  type EnrichedGroup,
  type LocalGroup,
  type ParallelCandidate,
  type ParallelCandidateSession,
  type SuccessResponse,
  type UUID,
  type YearOption,
} from "@/types/parallelSessions";

function parallelSaveErrorMessage(err: unknown): string {
  const code = err instanceof Error && "code" in err ? (err as ApiRequestError).code : undefined;
  if (code === ApiError.PARALLEL_GROUPS_NOT_CANDIDATES) {
    return "As turmas selecionadas não são candidatas a paralelas.";
  }
  return err instanceof Error ? err.message : "Erro ao guardar";
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  const data: unknown = await response.json();
  return data as T;
}

function toggleSet<T>(prev: Set<T>, value: T): Set<T> {
  const next = new Set(prev);
  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }
  return next;
}

export interface UseParallelSessionsReturn {
  degrees: DegreeOption[];
  loadingDegrees: boolean;
  degreesError: string | null;
  selectedDegree: DegreeOption | null;

  years: YearOption[];
  loadingYears: boolean;
  yearsError: string | null;
  selectedYearIds: Set<UUID>;
  yearsWithCandidates: YearOption[];

  loadingCandidates: boolean;
  candidatesError: string | null;
  parallelCandidates: ParallelCandidate[];
  filteredCandidates: ParallelCandidate[];
  candidatesBySubject: Map<string, DisplayCandidate[]>;
  groupsBySubject: Map<string, EnrichedGroup[]>;

  groups: LocalGroup[];
  savedGroupIds: Set<string>;
  pendingSelection: Set<UUID>;

  saving: boolean;
  saveStatus: { type: "success" | "error"; message: string } | null;
  isDirty: boolean;

  showUnsavedModal: boolean;
  setShowUnsavedModal: Dispatch<SetStateAction<boolean>>;
  showResetModal: boolean;
  setShowResetModal: Dispatch<SetStateAction<boolean>>;

  handleDegreeClick: (degree: DegreeOption) => void;
  handleYearToggle: (yearId: UUID) => void;
  handleSessionPendingToggle: (sessionId: UUID) => void;
  handleSelectAllForCandidate: (sessions: ParallelCandidateSession[]) => void;
  handleCreateGroup: (blockIds: UUID[], candidate: DisplayCandidate) => void;
  handleRemoveGroup: (groupId: string) => void;
  handleBack: () => void;
  handleNavigateHome: () => void;
  handleSave: () => Promise<void>;
  handleSaveAndExit: () => Promise<void>;
  handleExitWithoutSaving: () => void;
  handleReset: () => void;
  confirmReset: () => void;
}

export function useParallelSessions(): UseParallelSessionsReturn {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const draftGroupsByDegree = useRef<Record<string, LocalGroup[]>>({});
  const savedGroupsByDegree = useRef<Record<string, LocalGroup[]>>({});
  const allGroupsFromServer = useRef<LocalGroup[]>([]);

  const [restoredState] = useState<{
    degreeId: string;
    yearIds: string[];
  } | null>(() => {
    const raw = sessionStorage.getItem(`parallelClasses-${projectId ?? ""}`);
    if (!raw) return null;
    sessionStorage.removeItem(`parallelClasses-${projectId ?? ""}`);
    try {
      return JSON.parse(raw) as { degreeId: string; yearIds: string[] };
    } catch {
      return null;
    }
  });

  const [degrees, setDegrees] = useState<DegreeOption[]>([]);
  const [loadingDegrees, setLoadingDegrees] = useState(false);
  const [degreesError, setDegreesError] = useState<string | null>(null);

  const [selectedDegree, setSelectedDegree] = useState<DegreeOption | null>(null);

  const [years, setYears] = useState<YearOption[]>([]);
  const [loadingYears, setLoadingYears] = useState(false);
  const [yearsError, setYearsError] = useState<string | null>(null);
  const [selectedYearIds, setSelectedYearIds] = useState<Set<UUID>>(new Set());

  const [parallelCandidates, setParallelCandidates] = useState<ParallelCandidate[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [candidatesError, setCandidatesError] = useState<string | null>(null);

  const [groups, setGroups] = useState<LocalGroup[]>([]);
  const [savedSnapshot, setSavedSnapshot] = useState<LocalGroup[]>([]);
  const [pendingSelection, setPendingSelection] = useState<Set<UUID>>(new Set());

  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [showUnsavedModal, setShowUnsavedModal] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const pendingRoute = useRef<string>("");

  const projectIdNum = useMemo(() => Number(projectId), [projectId]);

  useEffect(() => {
    if (!projectId || Number.isNaN(projectIdNum)) return;

    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingDegrees(true);
    setDegreesError(null);

    fetchJson<SuccessResponse<{ degrees: DegreeOption[]; count: number }>>(
      `/api/projects/${projectIdNum}/degrees/with-parallel-candidates/`,
    )
      .then((response) => {
        if (cancelled) return;
        const fetchedDegrees = response.data.degrees;
        setDegrees(fetchedDegrees);
        if (restoredState?.degreeId) {
          const saved = fetchedDegrees.find((d) => d.id === restoredState.degreeId);
          if (saved) setSelectedDegree(saved);
        } else {
          const leic = fetchedDegrees.find((d) => d.acronym.toUpperCase() === "L.EIC");
          if (leic) setSelectedDegree(leic);
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setDegreesError(err instanceof Error ? err.message : "Failed to load degrees");
      })
      .finally(() => {
        if (!cancelled) setLoadingDegrees(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, projectIdNum, restoredState]);

  useEffect(() => {
    if (!selectedDegree || !projectId || Number.isNaN(projectIdNum)) return;

    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingYears(true);
    setYearsError(null);
    setYears([]);
    setSelectedYearIds(new Set());

    fetchJson<SuccessResponse<{ years: YearOption[] }>>(
      `/api/projects/${projectIdNum}/degrees/${selectedDegree.id}`,
    )
      .then((response) => {
        if (cancelled) return;
        const fetched = response.data.years;
        setYears(fetched);
        if (restoredState?.yearIds && restoredState.degreeId === selectedDegree.id) {
          const savedSet = new Set(restoredState.yearIds);
          setSelectedYearIds(new Set(fetched.filter((y) => savedSet.has(y.id)).map((y) => y.id)));
        } else {
          setSelectedYearIds(new Set(fetched.map((y) => y.id)));
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setYearsError(err instanceof Error ? err.message : "Failed to load years");
      })
      .finally(() => {
        if (!cancelled) setLoadingYears(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, projectIdNum, restoredState, selectedDegree]);

  useEffect(() => {
    if (!selectedDegree || !projectId || Number.isNaN(projectIdNum)) return;

    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingCandidates(true);
    setCandidatesError(null);
    setParallelCandidates([]);
    setPendingSelection(new Set());
    setGroups([]);
    setSavedSnapshot([]);

    const params = new URLSearchParams({ degree_id: selectedDegree.id });

    Promise.all([
      fetchJson<SuccessResponse<ParallelCandidate[]>>(
        `/api/projects/${projectIdNum}/parallel-candidates?${params.toString()}`,
      ),
      api.get<SuccessResponse<Record<string, string[]>>>(
        `/api/projects/${projectIdNum}/parallel-groups`,
      ),
    ])
      .then(([candidatesRes, groupsRes]) => {
        if (cancelled) return;
        setParallelCandidates(candidatesRes.data);
        const degreeBlockIds = new Set(
          candidatesRes.data.flatMap((c) => (c.sessions ?? []).map((s) => s.original_block_id)),
        );
        const allLoaded = Object.entries(groupsRes.data).map(([id, blockIds]) => ({
          id,
          blockIds,
        }));
        allGroupsFromServer.current = allLoaded;
        const loadedGroups = allLoaded.filter((g) =>
          g.blockIds.every((bid) => degreeBlockIds.has(bid)),
        );
        savedGroupsByDegree.current[selectedDegree.id] = loadedGroups;
        const draft = draftGroupsByDegree.current[selectedDegree.id];
        setGroups(draft ?? loadedGroups);
        setSavedSnapshot(loadedGroups);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setCandidatesError(
          err instanceof Error ? err.message : "Failed to load parallel candidates",
        );
      })
      .finally(() => {
        if (!cancelled) setLoadingCandidates(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, projectIdNum, selectedDegree]);

  const yearsWithCandidates = useMemo(() => {
    const numbersWithData = new Set(
      parallelCandidates.map((c) => c.year).filter((y): y is number => y != null),
    );
    return years.filter((y) => numbersWithData.has(y.number));
  }, [years, parallelCandidates]);

  const selectedYearNumbers = useMemo(
    () =>
      new Set(yearsWithCandidates.filter((y) => selectedYearIds.has(y.id)).map((y) => y.number)),
    [yearsWithCandidates, selectedYearIds],
  );

  const filteredCandidates = useMemo(
    () => parallelCandidates.filter((c) => c.year == null || selectedYearNumbers.has(c.year)),
    [parallelCandidates, selectedYearNumbers],
  );

  const assignedBlockIds = useMemo(() => new Set(groups.flatMap((g) => g.blockIds)), [groups]);

  const blockMetaMap = useMemo(() => {
    const map = new Map<UUID, BlockMeta>();
    for (const c of parallelCandidates) {
      for (const s of c.sessions ?? []) {
        map.set(s.original_block_id, {
          subject_name: c.subject_name ?? "Sessão",
          weekday: c.session_weekday ?? "",
          start_time: c.session_start_time ?? 0,
          class_codes: s.class_codes,
          session_type: s.session_type,
          session_week: c.session_week,
        });
      }
    }
    return map;
  }, [parallelCandidates]);

  const unassignedCandidates = useMemo(() => {
    return filteredCandidates
      .map((c) => ({
        ...c,
        sessions: (c.sessions ?? []).filter((s) => !assignedBlockIds.has(s.original_block_id)),
      }))
      .filter((c) => c.sessions.length > 0);
  }, [filteredCandidates, assignedBlockIds]);

  const displayCandidates = useMemo((): DisplayCandidate[] => {
    const fingerprint = (c: (typeof unassignedCandidates)[0]): string =>
      (c.sessions ?? [])
        .flatMap((s) => s.class_codes)
        .sort()
        .join("|");

    const byKey = new Map<string, typeof unassignedCandidates>();
    for (const c of unassignedCandidates) {
      const key = `${c.subject_name ?? ""}|${c.session_weekday ?? ""}|${c.session_start_time ?? 0}|${fingerprint(c)}`;
      const list = byKey.get(key);
      if (list) list.push(c);
      else byKey.set(key, [c]);
    }

    const timeToFpCount = new Map<string, Set<string>>();
    for (const c of unassignedCandidates) {
      const timeKey = `${c.subject_name ?? ""}|${c.session_weekday ?? ""}|${c.session_start_time ?? 0}`;
      const fp = fingerprint(c);
      let set = timeToFpCount.get(timeKey);
      if (!set) {
        set = new Set();
        timeToFpCount.set(timeKey, set);
      }
      set.add(fp);
    }

    const result: DisplayCandidate[] = [];
    for (const candidates of byKey.values()) {
      const [rep, ...absorbed] = candidates;
      if (!rep) continue;
      const timeKey = `${rep.subject_name ?? ""}|${rep.session_weekday ?? ""}|${rep.session_start_time ?? 0}`;
      const showWeek = (timeToFpCount.get(timeKey)?.size ?? 0) > 1;
      const displayWeeks = candidates.map((c) => c.session_week ?? "").filter(Boolean);
      result.push({
        ...rep,
        showWeek,
        displayWeeks,
        equivalentCandidates: absorbed,
      });
    }
    return result;
  }, [unassignedCandidates]);

  const candidatesBySubject = useMemo(() => {
    const map = new Map<string, DisplayCandidate[]>();
    for (const c of displayCandidates) {
      const key = c.subject_name ?? "Sessão";
      const list = map.get(key);
      if (list) list.push(c);
      else map.set(key, [c]);
    }
    for (const candidates of map.values()) {
      candidates.sort((a, b) => {
        const dayDiff =
          (DAY_ORDER[a.session_weekday ?? ""] ?? 99) - (DAY_ORDER[b.session_weekday ?? ""] ?? 99);
        if (dayDiff !== 0) return dayDiff;
        const timeDiff = (a.session_start_time ?? 0) - (b.session_start_time ?? 0);
        if (timeDiff !== 0) return timeDiff;
        const aWeek = a.displayWeeks[0] ?? "";
        const bWeek = b.displayWeeks[0] ?? "";
        return aWeek < bWeek ? -1 : aWeek > bWeek ? 1 : 0;
      });
    }
    return map;
  }, [displayCandidates]);

  const groupsBySubject = useMemo(() => {
    const enriched: EnrichedGroup[] = groups.map((group) => {
      const metas = group.blockIds
        .map((id) => blockMetaMap.get(id))
        .filter((m): m is BlockMeta => m != null);
      const first = metas[0];
      return {
        group,
        subject_name: first?.subject_name ?? "Sessão",
        weekday: first?.weekday ?? "",
        start_time: first?.start_time ?? 0,
        session_week: first?.session_week,
        sessions: metas,
      };
    });

    const map = new Map<string, EnrichedGroup[]>();
    for (const item of enriched) {
      const list = map.get(item.subject_name);
      if (list) list.push(item);
      else map.set(item.subject_name, [item]);
    }
    return map;
  }, [groups, blockMetaMap]);

  const savedGroupIds = useMemo(() => new Set(savedSnapshot.map((g) => g.id)), [savedSnapshot]);

  const isDirty = useMemo(() => {
    if (groups.length !== savedSnapshot.length) return true;
    return groups.some((g) => !savedGroupIds.has(g.id));
  }, [groups, savedSnapshot, savedGroupIds]);

  const backRoute = ROUTES.SCHEDULE.replace(":projectId", projectId ?? "");

  const handleDegreeClick = (degree: DegreeOption) => {
    if (selectedDegree && selectedDegree.id !== degree.id) {
      draftGroupsByDegree.current[selectedDegree.id] = [...groups];
    }
    setSelectedDegree((prev) => {
      if (prev?.id === degree.id) {
        setYears([]);
        setSelectedYearIds(new Set());
        setParallelCandidates([]);
        setCandidatesError(null);
        setYearsError(null);
        return null;
      }
      return degree;
    });
  };

  const handleYearToggle = (yearId: UUID) => {
    setSelectedYearIds((prev) => toggleSet(prev, yearId));
  };

  const handleSessionPendingToggle = (sessionId: UUID) => {
    setPendingSelection((prev) => toggleSet(prev, sessionId));
  };

  const handleSelectAllForCandidate = (sessions: ParallelCandidateSession[]) => {
    const ids = sessions.map((s) => s.original_block_id);
    const allPending = ids.every((id) => pendingSelection.has(id));
    setPendingSelection((prev) => {
      const next = new Set(prev);
      if (allPending) ids.forEach((id) => next.delete(id));
      else ids.forEach((id) => next.add(id));
      return next;
    });
  };

  const handleCreateGroup = (blockIds: UUID[], candidate: DisplayCandidate) => {
    if (blockIds.length < 2) return;
    const allBlockIds = [...blockIds];
    for (const absorbed of candidate.equivalentCandidates) {
      const codeToId = new Map<string, UUID>();
      for (const s of absorbed.sessions ?? []) {
        codeToId.set([...s.class_codes].sort().join(","), s.original_block_id);
      }
      for (const id of blockIds) {
        const repSession = (candidate.sessions ?? []).find((s) => s.original_block_id === id);
        if (!repSession) continue;
        const key = [...repSession.class_codes].sort().join(",");
        const absId = codeToId.get(key);
        if (absId) allBlockIds.push(absId);
      }
    }
    setGroups((prev) => [...prev, { id: crypto.randomUUID(), blockIds: allBlockIds }]);
    setPendingSelection((prev) => {
      const next = new Set(prev);
      blockIds.forEach((id) => next.delete(id));
      return next;
    });
  };

  const handleRemoveGroup = (groupId: string) => {
    setGroups((prev) => prev.filter((g) => g.id !== groupId));
  };

  const handleBack = () => {
    pendingRoute.current = backRoute;
    if (isDirty) {
      setShowUnsavedModal(true);
    } else {
      void navigate(backRoute);
    }
  };

  const handleNavigateHome = () => {
    pendingRoute.current = ROUTES.HOME;
    if (isDirty) {
      setShowUnsavedModal(true);
    } else {
      void navigate(ROUTES.HOME);
    }
  };

  const performSave = async () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;

    // Build the full set of block IDs that belong to any degree we have loaded
    const knownBlockIds = new Set([
      ...parallelCandidates.flatMap((c) => (c.sessions ?? []).map((s) => s.original_block_id)),
      ...Object.values(savedGroupsByDegree.current).flatMap((gs) => gs.flatMap((g) => g.blockIds)),
    ]);

    // Groups from server whose blocks are entirely unknown (degrees never visited)
    const foreignGroups = allGroupsFromServer.current.filter(
      (g) => !g.blockIds.some((bid) => knownBlockIds.has(bid)),
    );

    // Collect groups for all known degrees
    const allGroups: LocalGroup[] = [...groups];
    for (const [degId, saved] of Object.entries(savedGroupsByDegree.current)) {
      if (selectedDegree && degId === selectedDegree.id) continue;
      const draft = draftGroupsByDegree.current[degId];
      allGroups.push(...(draft ?? saved));
    }
    allGroups.push(...foreignGroups);

    const payload = allGroups
      .map((g) => ({ classes: g.blockIds }))
      .filter((g) => g.classes.length >= 2);
    await api.post(`/api/projects/${projectIdNum}/parallel-groups`, { groups: payload });
    sessionStorage.setItem(
      `parallelClasses-${projectId ?? ""}`,
      JSON.stringify({ degreeId: selectedDegree?.id, yearIds: [...selectedYearIds] }),
    );
  };

  const handleExitWithoutSaving = () => {
    void navigate(pendingRoute.current || backRoute);
  };

  const handleReset = () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    setShowResetModal(true);
  };

  const confirmReset = () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    api
      .post(`/api/projects/${projectIdNum}/parallel-groups`, { groups: [] })
      .then(() => {
        window.location.reload();
      })
      .catch((err: unknown) => {
        setShowResetModal(false);
        setSaveStatus({
          type: "error",
          message: err instanceof Error ? err.message : "Erro ao recomeçar",
        });
      });
  };

  const handleSave = async () => {
    if (!isDirty) return;
    setSaving(true);
    setSaveStatus(null);
    try {
      await performSave();
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
      const saved = [...groups];
      setSavedSnapshot(saved);
      if (selectedDegree) {
        savedGroupsByDegree.current[selectedDegree.id] = saved;
      }
      for (const [degId, draft] of Object.entries(draftGroupsByDegree.current)) {
        savedGroupsByDegree.current[degId] = draft;
        delete draftGroupsByDegree.current[degId];
      }
      setSaveStatus({ type: "success", message: "Guardado com sucesso" });
    } catch (err) {
      setSaveStatus({
        type: "error",
        message: parallelSaveErrorMessage(err),
      });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAndExit = async () => {
    setSaving(true);
    setSaveStatus(null);
    try {
      await performSave();
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
      if (selectedDegree) {
        savedGroupsByDegree.current[selectedDegree.id] = [...groups];
      }
      for (const [degId, draft] of Object.entries(draftGroupsByDegree.current)) {
        savedGroupsByDegree.current[degId] = draft;
        delete draftGroupsByDegree.current[degId];
      }
      void navigate(pendingRoute.current || backRoute);
    } catch (err) {
      setShowUnsavedModal(false);
      setSaveStatus({
        type: "error",
        message: parallelSaveErrorMessage(err),
      });
    } finally {
      setSaving(false);
    }
  };

  return {
    degrees,
    loadingDegrees,
    degreesError,
    selectedDegree,
    years,
    loadingYears,
    yearsError,
    selectedYearIds,
    yearsWithCandidates,
    loadingCandidates,
    candidatesError,
    parallelCandidates,
    filteredCandidates,
    candidatesBySubject,
    groupsBySubject,
    groups,
    savedGroupIds,
    pendingSelection,
    saving,
    saveStatus,
    isDirty,
    showUnsavedModal,
    setShowUnsavedModal,
    showResetModal,
    setShowResetModal,
    handleDegreeClick,
    handleYearToggle,
    handleSessionPendingToggle,
    handleSelectAllForCandidate,
    handleCreateGroup,
    handleRemoveGroup,
    handleBack,
    handleNavigateHome,
    handleSave,
    handleSaveAndExit,
    handleExitWithoutSaving,
    handleReset,
    confirmReset,
  };
}
