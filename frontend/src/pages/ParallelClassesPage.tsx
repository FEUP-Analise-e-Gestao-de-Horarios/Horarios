import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/api/client";
import { ROUTES } from "@/routes";

type UUID = string;

interface YearOption {
  id: UUID;
  number: number;
}

interface DegreeOption {
  id: UUID;
  name: string;
  acronym: string;
}

interface ParallelCandidateSession {
  original_block_id: UUID;
  class_codes: string[];
  session_type?: string;
}

interface ParallelCandidate {
  id: UUID;
  candidate_group_id?: UUID;
  subject_name?: string;
  session_start_time?: number;
  session_weekday?: string;
  session_duration?: number;
  session_week?: string;
  sessions?: ParallelCandidateSession[];
  year?: number;
  degree_id?: string;
  degree_acronym?: string;
}

interface SuccessResponse<T> {
  message: string;
  data: T;
}

interface LocalGroup {
  id: string;
  blockIds: UUID[];
}

interface BlockMeta {
  subject_name: string;
  weekday: string;
  start_time: number;
  class_codes: string[];
  session_type?: string;
  session_week?: string;
}

interface DisplayCandidate extends ParallelCandidate {
  showWeek: boolean;
  displayWeeks: string[];
  equivalentCandidates: ParallelCandidate[];
}

function formatWeekDate(dateStr: string): string {
  const parts = dateStr.split("-");
  return `${parts[2]}/${parts[1]}`;
}

function formatTime(t: number): string {
  const s = String(t).padStart(4, "0");
  return `${s.slice(0, 2)}:${s.slice(2)}`;
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

interface DarkPillProps {
  label: string;
  active: boolean;
  onClick: () => void;
}

function DarkPill({ label, active, onClick }: DarkPillProps) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm font-semibold border cursor-pointer transition-all whitespace-nowrap ${
        active
          ? "bg-[#ffc107] border-[#b8860b] text-[#222]"
          : "bg-transparent border-gray-600 text-gray-300 hover:border-gray-400 hover:bg-white/5"
      }`}
    >
      {label}
    </button>
  );
}

function HeaderPillSkeleton() {
  return (
    <>
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-8 w-16 rounded-full bg-gray-700 animate-pulse" />
      ))}
    </>
  );
}

// TODO: replace with degrees derived from the logged-in teacher's assignments
const PRIORITY_DEGREE_ACRONYMS = ["L.EIC", "M.EIC", "M.IA"];

const DAY_ORDER: Record<string, number> = {
  monday: 0,
  tuesday: 1,
  wednesday: 2,
  thursday: 3,
  friday: 4,
};

const DAY_CONFIG: Record<string, { short: string; bg: string; text: string }> = {
  monday: { short: "SEG", bg: "bg-blue-500", text: "text-white" },
  tuesday: { short: "TER", bg: "bg-emerald-500", text: "text-white" },
  wednesday: { short: "QUA", bg: "bg-violet-500", text: "text-white" },
  thursday: { short: "QUI", bg: "bg-orange-500", text: "text-white" },
  friday: { short: "SEX", bg: "bg-rose-500", text: "text-white" },
};
const SESSION_TYPE_CONFIG: Record<string, { bg: string; text: string }> = {
  TP: { bg: "bg-blue-100", text: "text-blue-700" },
  OT: { bg: "bg-violet-100", text: "text-violet-700" },
  PL: { bg: "bg-emerald-100", text: "text-emerald-700" },
  T: { bg: "bg-orange-100", text: "text-orange-700" },
  S: { bg: "bg-rose-100", text: "text-rose-700" },
};
const SESSION_TYPE_DEFAULT = { bg: "bg-gray-100", text: "text-gray-600" };

function CandidatesLoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-12 rounded-xl bg-[#e8e8e8] animate-pulse" />
      ))}
    </div>
  );
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

export default function ParallelClassesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
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
  const [showAllDegrees, setShowAllDegrees] = useState(false);

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

  const priorityDegrees = useMemo(
    () =>
      PRIORITY_DEGREE_ACRONYMS.flatMap((acronym) => {
        const match = degrees.find((d) => d.acronym === acronym);
        return match ? [match] : [];
      }),
    [degrees],
  );

  const otherDegrees = useMemo(
    () => degrees.filter((d) => !PRIORITY_DEGREE_ACRONYMS.includes(d.acronym)),
    [degrees],
  );

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
        id: rep.id ?? "",
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

  const isDirty = useMemo(() => {
    if (groups.length !== savedSnapshot.length) return true;
    const snapshotIds = new Set(savedSnapshot.map((g) => g.id));
    return groups.some((g) => !snapshotIds.has(g.id));
  }, [groups, savedSnapshot]);

  const backRoute = ROUTES.SCHEDULE.replace(":projectId", projectId ?? "");

  const handleBack = () => {
    if (isDirty) {
      setShowUnsavedModal(true);
    } else {
      void navigate(backRoute);
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
    const allGroups: LocalGroup[] = [...groups]; // current degree
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
        message: err instanceof Error ? err.message : "Erro ao guardar",
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
      if (selectedDegree) {
        savedGroupsByDegree.current[selectedDegree.id] = [...groups];
      }
      for (const [degId, draft] of Object.entries(draftGroupsByDegree.current)) {
        savedGroupsByDegree.current[degId] = draft;
        delete draftGroupsByDegree.current[degId];
      }
      void navigate(backRoute);
    } catch (err) {
      setShowUnsavedModal(false);
      setSaveStatus({
        type: "error",
        message: err instanceof Error ? err.message : "Erro ao guardar",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-[#f0eeeb]">
      <header className="shrink-0 sticky top-0 z-50 px-6 py-3 bg-[#1e2028] flex items-center gap-2 w-full flex-wrap border-b border-gray-700">
        <button
          onClick={handleBack}
          className="bg-[#8c2d19] text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#a33520] transition-colors cursor-pointer"
        >
          ← Voltar
        </button>

        <div className="w-px h-6 bg-gray-600 mx-1" />

        <span className="text-[11px] font-bold tracking-widest uppercase text-gray-400 whitespace-nowrap">
          Curso
        </span>

        {loadingDegrees ? (
          <HeaderPillSkeleton />
        ) : degreesError ? (
          <span className="text-xs text-red-400">{degreesError}</span>
        ) : (
          <>
            {priorityDegrees.map((d) => (
              <DarkPill
                key={d.id}
                label={d.acronym}
                active={selectedDegree?.id === d.id}
                onClick={() => handleDegreeClick(d)}
              />
            ))}
            {showAllDegrees &&
              otherDegrees.map((d) => (
                <DarkPill
                  key={d.id}
                  label={d.acronym}
                  active={selectedDegree?.id === d.id}
                  onClick={() => handleDegreeClick(d)}
                />
              ))}
            {otherDegrees.length > 0 && (
              <button
                onClick={() => setShowAllDegrees((prev) => !prev)}
                className="px-3 py-1.5 rounded-full text-sm font-semibold border cursor-pointer transition-all whitespace-nowrap bg-transparent border-gray-600 text-gray-300 hover:border-gray-400 hover:bg-white/5"
              >
                {showAllDegrees ? "Menos ▲" : `+${otherDegrees.length} ▼`}
              </button>
            )}
          </>
        )}

        {selectedDegree && (
          <>
            <div className="w-px h-6 bg-gray-600 mx-1" />
            <span className="text-[11px] font-bold tracking-widest uppercase text-gray-400 whitespace-nowrap">
              Ano
            </span>
            {loadingYears ? (
              <HeaderPillSkeleton />
            ) : yearsError ? (
              <span className="text-xs text-red-400">{yearsError}</span>
            ) : (
              yearsWithCandidates.map((y) => (
                <DarkPill
                  key={y.id}
                  label={`${y.number}º Ano`}
                  active={selectedYearIds.has(y.id)}
                  onClick={() => handleYearToggle(y.id)}
                />
              ))
            )}
          </>
        )}

        <div className="ml-auto flex items-center gap-2">
          {saveStatus && (
            <span
              className={`text-xs font-semibold ${saveStatus.type === "success" ? "text-green-400" : "text-red-400"}`}
            >
              {saveStatus.message}
            </span>
          )}
          <button
            onClick={handleReset}
            disabled={saving}
            className="bg-transparent text-red-400 font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            Recomeçar
          </button>
          <button
            onClick={() => void handleSave()}
            disabled={saving}
            className="bg-[#ffc107] text-[#222] font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#e6ad06] transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {saving ? "A guardar..." : "Guardar"}
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-hidden">
        {!selectedDegree ? (
          <p className="text-sm text-[#aaa] text-center mt-16">
            Seleciona um curso para ver as sessões em paralelo.
          </p>
        ) : (
          <div className="h-full max-w-6xl mx-auto px-6 pt-6 flex gap-6">
            {/* Left column: Por selecionar */}
            <div className="flex-1 min-w-0 flex flex-col min-h-0">
              <h2 className="font-bold text-[#333] text-base mb-3 shrink-0">Por selecionar</h2>
              <div className="flex-1 overflow-y-auto pb-6 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                {loadingCandidates ? (
                  <CandidatesLoadingSkeleton />
                ) : candidatesError ? (
                  <p className="text-sm text-red-600">{candidatesError}</p>
                ) : !filteredCandidates.length ? (
                  <p className="text-sm text-[#aaa]">Sem sessões em paralelo.</p>
                ) : candidatesBySubject.size === 0 ? (
                  <p className="text-xs text-[#aaa] text-center py-8">
                    Todas as sessões foram atribuídas a grupos.
                  </p>
                ) : (
                  <div className="flex flex-col gap-4">
                    {[...candidatesBySubject.entries()].map(([subjectName, candidates]) => {
                      const hasWeeks = candidates.some((c) => c.showWeek);

                      const weekMap = new Map<string, DisplayCandidate[]>();
                      for (const c of candidates) {
                        const weekKey = c.displayWeeks[0] ?? "";
                        const list = weekMap.get(weekKey);
                        if (list) list.push(c);
                        else weekMap.set(weekKey, [c]);
                      }
                      const sortedWeeks = [...weekMap.keys()].sort();

                      const renderRow = (candidate: DisplayCandidate, rowIdx: number) => {
                        const sessions = candidate.sessions ?? [];
                        const selectedInRow = sessions
                          .map((s) => s.original_block_id)
                          .filter((id) => pendingSelection.has(id));
                        const day = DAY_CONFIG[candidate.session_weekday ?? ""] ?? {
                          short: "?",
                          bg: "bg-gray-400",
                          text: "text-white",
                        };
                        return (
                          <tr
                            key={candidate.id}
                            className={`bg-white hover:bg-[#fffdf5] transition-colors ${rowIdx > 0 ? "border-t border-[#f0f0f0]" : ""}`}
                          >
                            <td className="px-3 py-3 align-top">
                              <div className="flex flex-col items-start gap-0.5">
                                <span
                                  className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md ${day.bg} ${day.text}`}
                                >
                                  {day.short}
                                </span>
                                {!hasWeeks &&
                                  candidate.showWeek &&
                                  candidate.displayWeeks.length > 0 && (
                                    <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded bg-gray-200 text-gray-600 whitespace-nowrap tabular-nums">
                                      {candidate.displayWeeks.length > 1
                                        ? candidate.displayWeeks.map(formatWeekDate).join(", ")
                                        : formatWeekDate(candidate.displayWeeks[0] ?? "")}
                                    </span>
                                  )}
                              </div>
                            </td>
                            <td className="px-3 py-3 align-top font-bold text-[#333] tabular-nums whitespace-nowrap">
                              {candidate.session_start_time != null
                                ? formatTime(candidate.session_start_time)
                                : "—"}
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex flex-col gap-1.5">
                                {sessions.map((session) => {
                                  const checked = pendingSelection.has(session.original_block_id);
                                  const typeLabel = session.session_type ?? null;
                                  const typeStyle = typeLabel
                                    ? (SESSION_TYPE_CONFIG[typeLabel] ?? SESSION_TYPE_DEFAULT)
                                    : null;
                                  const pills = (
                                    <div className="flex items-center gap-1">
                                      {typeLabel && typeStyle && (
                                        <span
                                          className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${typeStyle.bg} ${typeStyle.text}`}
                                        >
                                          {typeLabel}
                                        </span>
                                      )}
                                      {session.class_codes.map((code: string) => (
                                        <span
                                          key={`${session.original_block_id}-${code}`}
                                          className={`rounded px-2 py-0.5 text-[12px] font-semibold transition-colors ${
                                            checked
                                              ? "bg-[#ffc107] text-[#222]"
                                              : "bg-[#f0f0f0] text-[#666]"
                                          }`}
                                        >
                                          {code}
                                        </span>
                                      ))}
                                    </div>
                                  );
                                  return sessions.length > 1 ? (
                                    <label
                                      key={session.original_block_id}
                                      className="flex items-center gap-1.5 cursor-pointer"
                                    >
                                      <input
                                        type="checkbox"
                                        checked={checked}
                                        onChange={() =>
                                          handleSessionPendingToggle(session.original_block_id)
                                        }
                                        className="w-3.5 h-3.5 accent-[#ffc107] cursor-pointer shrink-0"
                                      />
                                      {pills}
                                    </label>
                                  ) : (
                                    <div key={session.original_block_id}>{pills}</div>
                                  );
                                })}
                                {sessions.length > 1 && (
                                  <div className="flex items-center justify-between mt-0.5">
                                    <label className="flex items-center gap-1.5 cursor-pointer">
                                      <input
                                        type="checkbox"
                                        checked={
                                          sessions.length > 0 &&
                                          sessions.every((s) =>
                                            pendingSelection.has(s.original_block_id),
                                          )
                                        }
                                        onChange={() => handleSelectAllForCandidate(sessions)}
                                        className="w-3.5 h-3.5 accent-[#ffc107] cursor-pointer shrink-0"
                                      />
                                      <span className="text-[11px] text-[#999] font-semibold whitespace-nowrap">
                                        selecionar todas
                                      </span>
                                    </label>
                                    {selectedInRow.length >= 2 && (
                                      <button
                                        onClick={() => handleCreateGroup(selectedInRow, candidate)}
                                        className="ml-3 bg-[#1e2028] text-white font-semibold px-3 py-1 rounded-lg text-[11px] hover:bg-[#2a2d37] transition-colors whitespace-nowrap cursor-pointer"
                                      >
                                        Criar Grupo
                                      </button>
                                    )}
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      };

                      return (
                        <div
                          key={subjectName}
                          className="overflow-hidden rounded-2xl border border-[#e8e8e8] shadow-sm"
                        >
                          <div className="px-4 py-2.5 bg-[#fafafa] border-b border-[#e8e8e8]">
                            <p className="font-semibold text-[#222] text-sm">{subjectName}</p>
                          </div>
                          <div className="overflow-x-auto [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                            <table className="min-w-full text-sm border-collapse">
                              <thead>
                                <tr className="bg-white border-b border-[#e8e8e8]">
                                  <th className="text-left px-3 py-2 text-[11px] font-bold tracking-widest uppercase text-[#999] w-[52px]">
                                    Dia
                                  </th>
                                  <th className="text-left px-3 py-2 text-[11px] font-bold tracking-widest uppercase text-[#999] w-[64px]">
                                    Hora
                                  </th>
                                  <th className="text-left px-4 py-2 text-[11px] font-bold tracking-widest uppercase text-[#999]">
                                    Turmas em paralelo
                                  </th>
                                </tr>
                              </thead>
                              <tbody>
                                {hasWeeks
                                  ? sortedWeeks.flatMap((weekKey, weekIdx) => [
                                      <tr
                                        key={`whdr-${weekKey}`}
                                        className="bg-[#f5f4f1] border-t border-[#e8e8e8]"
                                      >
                                        <td colSpan={3} className="px-3 py-1.5">
                                          <span className="text-[10px] font-bold tracking-widest uppercase text-[#888]">
                                            Semana {weekIdx + 1}
                                            {weekKey ? ` · ${formatWeekDate(weekKey)}` : ""}
                                          </span>
                                        </td>
                                      </tr>,
                                      ...(weekMap.get(weekKey) ?? []).map((c, i) =>
                                        renderRow(c, i),
                                      ),
                                    ])
                                  : candidates.map((c, i) => renderRow(c, i))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Right column: Selecionadas */}
            <div className="w-80 shrink-0 flex flex-col min-h-0">
              <h2 className="font-bold text-[#333] text-base mb-3 shrink-0">Selecionadas</h2>
              <div className="flex-1 overflow-y-auto pb-6 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                {loadingCandidates ? (
                  <CandidatesLoadingSkeleton />
                ) : groups.length === 0 ? (
                  <p className="text-xs text-[#aaa] text-center py-8">Nenhum grupo criado ainda.</p>
                ) : (
                  (() => {
                    const enriched = groups.map((group) => {
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

                    // Group by subject
                    const bySubject = new Map<string, typeof enriched>();
                    for (const item of enriched) {
                      const list = bySubject.get(item.subject_name);
                      if (list) list.push(item);
                      else bySubject.set(item.subject_name, [item]);
                    }

                    return (
                      <div className="flex flex-col gap-5">
                        {[...bySubject.entries()].map(([subjName, items]) => (
                          <div
                            key={subjName}
                            className="overflow-hidden rounded-2xl border border-[#d4d4d4] shadow-sm"
                          >
                            <div className="px-3 py-2 bg-[#e8e8e8] border-b border-[#d4d4d4]">
                              <p className="text-[11px] font-bold tracking-widest uppercase text-[#444]">
                                {subjName}
                              </p>
                            </div>
                            <div className="flex flex-col gap-2 p-2">
                              {items.map(
                                ({ group, weekday, start_time, session_week, sessions }) => {
                                  const day = DAY_CONFIG[weekday] ?? {
                                    short: "?",
                                    bg: "bg-gray-400",
                                    text: "text-white",
                                  };
                                  return (
                                    <div
                                      key={group.id}
                                      className="overflow-hidden rounded-xl border border-[#e8e8e8] shadow-sm bg-white"
                                    >
                                      <div className="px-3 py-1.5 bg-[#1e2028] flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                          <span
                                            className={`text-[10px] font-bold tracking-wider px-1.5 py-0.5 rounded ${day.bg} ${day.text}`}
                                          >
                                            {day.short}
                                          </span>
                                          {session_week && (
                                            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-gray-600 text-gray-300 tabular-nums whitespace-nowrap">
                                              {formatWeekDate(session_week)}
                                            </span>
                                          )}
                                          <span className="text-[11px] font-bold text-gray-300 tabular-nums">
                                            {formatTime(start_time)}
                                          </span>
                                        </div>
                                        <button
                                          onClick={() => handleRemoveGroup(group.id)}
                                          className="flex items-center justify-center w-5 h-5 rounded bg-red-600 hover:bg-red-500 transition-colors text-white text-xs font-bold leading-none cursor-pointer"
                                          title="Remover grupo"
                                        >
                                          ×
                                        </button>
                                      </div>
                                      <div className="px-3 py-2 flex flex-col gap-1 overflow-x-auto [&::-webkit-scrollbar]:h-1 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300/60">
                                        {sessions.map((meta, i) => {
                                          const typeLabel = meta.session_type ?? null;
                                          const typeStyle = typeLabel
                                            ? (SESSION_TYPE_CONFIG[typeLabel] ??
                                              SESSION_TYPE_DEFAULT)
                                            : null;
                                          return (
                                            <div key={i} className="flex items-center gap-1 w-max">
                                              {typeLabel && typeStyle && (
                                                <span
                                                  className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${typeStyle.bg} ${typeStyle.text}`}
                                                >
                                                  {typeLabel}
                                                </span>
                                              )}
                                              {meta.class_codes.map((code: string) => (
                                                <span
                                                  key={`${group.id}-${i}-${code}`}
                                                  className="rounded px-1.5 py-0.5 text-[11px] font-semibold bg-[#ffc107] text-[#222]"
                                                >
                                                  {code}
                                                </span>
                                              ))}
                                            </div>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  );
                                },
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })()
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {showResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-bold text-[#222] text-base mb-1">Tens a certeza?</h3>
            <p className="text-sm text-[#666] mb-6">
              Todas as seleções guardadas serão apagadas. Esta ação não pode ser desfeita.
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={confirmReset}
                className="bg-red-600 text-white font-semibold px-4 py-2 rounded-lg text-sm hover:bg-red-500 transition-colors cursor-pointer"
              >
                Recomeçar
              </button>
              <button
                onClick={() => setShowResetModal(false)}
                className="text-[#666] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition-colors cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
      {showUnsavedModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-bold text-[#222] text-base mb-1">Tens mudanças por guardar</h3>
            <p className="text-sm text-[#666] mb-6">
              Se saíres sem guardar, as alterações feitas serão perdidas.
            </p>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => void handleSaveAndExit()}
                disabled={saving}
                className="bg-[#ffc107] text-[#222] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-[#e6ad06] transition-colors disabled:opacity-50 cursor-pointer"
              >
                {saving ? "A guardar..." : "Guardar e sair"}
              </button>
              <button
                onClick={() => void navigate(backRoute)}
                disabled={saving}
                className="border border-red-400 text-red-500 font-semibold px-4 py-2 rounded-lg text-sm hover:bg-red-50 transition-colors disabled:opacity-50 cursor-pointer"
              >
                Sair sem guardar
              </button>
              <button
                onClick={() => setShowUnsavedModal(false)}
                disabled={saving}
                className="text-[#666] font-semibold px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition-colors disabled:opacity-50 cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
