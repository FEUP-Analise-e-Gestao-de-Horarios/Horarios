import { useEffect, useMemo, useState } from "react";
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

function formatTime(t: number): string {
  const s = String(t).padStart(4, "0");
  return `${s.slice(0, 2)}:${s.slice(2)}`;
}

function toggleSet<T>(prev: Set<T>, value: T): Set<T> {
  const next = new Set(prev);
  next.has(value) ? next.delete(value) : next.add(value);
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

  return response.json() as Promise<T>;
}

export default function ParallelClassesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [restoredState] = useState<{
    degreeId: string;
    yearIds: string[];
    activeTab: "por-selecionar" | "selecionados";
  } | null>(() => {
    const raw = sessionStorage.getItem(`parallelClasses-${projectId ?? ""}`);
    if (!raw) return null;
    sessionStorage.removeItem(`parallelClasses-${projectId ?? ""}`);
    try {
      return JSON.parse(raw);
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
  const [checkedSessions, setCheckedSessions] = useState<Set<UUID>>(new Set());
  const [initialSavedBlockIds, setInitialSavedBlockIds] = useState<Set<UUID>>(new Set());

  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [activeTab, setActiveTab] = useState<"por-selecionar" | "selecionados">(
    restoredState?.activeTab ?? "por-selecionar",
  );

  const projectIdNum = useMemo(() => Number(projectId), [projectId]);

  useEffect(() => {
    if (!projectId || Number.isNaN(projectIdNum)) return;

    let cancelled = false;
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
  }, [projectId, projectIdNum]);

  useEffect(() => {
    if (!selectedDegree || !projectId || Number.isNaN(projectIdNum)) return;

    let cancelled = false;
    setLoadingYears(true);
    setYearsError(null);
    setYears([]);
    setSelectedYearIds(new Set());

    fetchJson<SuccessResponse<{ years: YearOption[]; count: number }>>(
      `/api/projects/${projectIdNum}/degrees/${selectedDegree.id}/years/`,
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
  }, [projectId, projectIdNum, selectedDegree]);

  useEffect(() => {
    if (!selectedDegree || !projectId || Number.isNaN(projectIdNum)) return;

    let cancelled = false;
    setLoadingCandidates(true);
    setCandidatesError(null);
    setParallelCandidates([]);
    setCheckedSessions(new Set());

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
        const candidates = candidatesRes.data;
        setParallelCandidates(candidates);

        const savedIds = new Set(Object.values(groupsRes.data).flat());
        const preChecked = candidates
          .flatMap((c) => (c.sessions ?? []).map((s) => s.original_block_id))
          .filter((id) => savedIds.has(id));
        setCheckedSessions(new Set(preChecked));
        setInitialSavedBlockIds(savedIds);
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

  const tabFilteredCandidates = useMemo(() => {
    return filteredCandidates.filter((c) => {
      const wasSaved = (c.sessions ?? []).some((s) =>
        initialSavedBlockIds.has(s.original_block_id),
      );
      return activeTab === "selecionados" ? wasSaved : !wasSaved;
    });
  }, [filteredCandidates, initialSavedBlockIds, activeTab]);

  const allSelected = useMemo(
    () =>
      filteredCandidates.length > 0 &&
      filteredCandidates.every((c) =>
        (c.sessions ?? []).some((s) => initialSavedBlockIds.has(s.original_block_id)),
      ),
    [filteredCandidates, initialSavedBlockIds],
  );

  const candidatesBySubject = useMemo(() => {
    const map = new Map<string, ParallelCandidate[]>();
    for (const c of tabFilteredCandidates) {
      const key = c.subject_name ?? "Sessão";
      const list = map.get(key);
      if (list) list.push(c);
      else map.set(key, [c]);
    }
    for (const candidates of map.values()) {
      candidates.sort((a, b) => {
        const dayDiff =
          (DAY_ORDER[a.session_weekday ?? ""] ?? 99) - (DAY_ORDER[b.session_weekday ?? ""] ?? 99);
        return dayDiff !== 0 ? dayDiff : (a.session_start_time ?? 0) - (b.session_start_time ?? 0);
      });
    }
    return map;
  }, [tabFilteredCandidates]);

  const handleDegreeClick = (degree: DegreeOption) => {
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

  const handleSessionToggle = (sessionId: UUID) => {
    setCheckedSessions((prev) => toggleSet(prev, sessionId));
  };

  const handleReset = () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    if (
      !window.confirm(
        "Tens a certeza que queres recomeçar? Todas as seleções guardadas serão apagadas.",
      )
    )
      return;

    api
      .post(`/api/projects/${projectIdNum}/parallel-groups`, { groups: [] })
      .then(() => {
        window.location.reload();
      })
      .catch((err: unknown) => {
        setSaveStatus({
          type: "error",
          message: err instanceof Error ? err.message : "Erro ao recomeçar",
        });
      });
  };

  const handleSave = async () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;

    const groups = parallelCandidates
      .map((candidate) => ({
        classes: (candidate.sessions ?? [])
          .filter((s) => checkedSessions.has(s.original_block_id))
          .map((s) => s.original_block_id),
      }))
      .filter((g) => g.classes.length >= 2);

    setSaving(true);
    setSaveStatus(null);

    api
      .post<SuccessResponse<{ assigned: number }>>(
        `/api/projects/${projectIdNum}/parallel-groups`,
        { groups },
      )
      .then(() => {
        sessionStorage.setItem(
          `parallelClasses-${projectId ?? ""}`,
          JSON.stringify({
            degreeId: selectedDegree?.id,
            yearIds: [...selectedYearIds],
            activeTab,
          }),
        );
        window.location.reload();
      })
      .catch((err: unknown) => {
        setSaveStatus({
          type: "error",
          message: err instanceof Error ? err.message : "Erro ao guardar",
        });
      })
      .finally(() => {
        setSaving(false);
      });
  };

  const handleSelectAll = (candidate: ParallelCandidate) => {
    const ids = (candidate.sessions ?? []).map((s) => s.original_block_id);
    const allChecked = ids.every((id) => checkedSessions.has(id));
    setCheckedSessions((prev) => {
      const next = new Set(prev);
      if (allChecked) ids.forEach((id) => next.delete(id));
      else ids.forEach((id) => next.add(id));
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-[#f0eeeb]">
      <header className="sticky top-0 z-50 px-6 py-3 bg-[#1e2028] flex items-center gap-2 w-full flex-wrap border-b border-gray-700">
        <button
          onClick={() => void navigate(ROUTES.SCHEDULE.replace(":projectId", projectId ?? ""))}
          className="bg-[#8c2d19] text-white font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#a33520] transition-colors"
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
            className="bg-transparent text-red-400 font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap border border-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Recomeçar
          </button>
          <button
            onClick={() => void handleSave()}
            disabled={saving}
            className="bg-[#ffc107] text-[#222] font-semibold px-3.5 py-2 rounded text-sm whitespace-nowrap hover:bg-[#e6ad06] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? "A guardar..." : "Guardar"}
          </button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-9 pb-20">
        {!selectedDegree ? (
          <p className="text-sm text-[#aaa] text-center mt-16">
            Seleciona um curso para ver as sessões em paralelo.
          </p>
        ) : (
          <div>
            <div className="flex gap-1 mb-5 border-b border-[#e0e0e0]">
              {(["por-selecionar", "selecionados"] as const).map((tab) => {
                const label = tab === "por-selecionar" ? "Por selecionar" : "Selecionados";
                const isActive = activeTab === tab;
                return (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-2 text-sm font-semibold border-b-2 -mb-px transition-colors whitespace-nowrap ${
                      isActive
                        ? "border-[#ffc107] text-[#222]"
                        : "border-transparent text-[#999] hover:text-[#555]"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>

            {loadingCandidates ? (
              <CandidatesLoadingSkeleton />
            ) : candidatesError ? (
              <p className="text-sm text-red-600">{candidatesError}</p>
            ) : !filteredCandidates.length ? (
              <p className="text-sm text-[#aaa]">Sem sessões em paralelo.</p>
            ) : (
              <div className="flex flex-col gap-4">
                {activeTab === "por-selecionar" && allSelected && (
                  <p className="text-xs text-[#aaa] text-center">
                    Todas as turmas em paralelo foram selecionadas.
                  </p>
                )}
                {[...candidatesBySubject.entries()].map(([subjectName, candidates]) => (
                  <div
                    key={subjectName}
                    className="overflow-hidden rounded-2xl border border-[#e8e8e8] shadow-sm"
                  >
                    <div className="px-4 py-2.5 bg-[#fafafa] border-b border-[#e8e8e8]">
                      <p className="font-semibold text-[#222] text-sm">{subjectName}</p>
                    </div>
                    <table className="w-full text-sm border-collapse">
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
                        {candidates.map((candidate, rowIdx) => {
                          const sessions = candidate.sessions ?? [];
                          const isPair = sessions.length === 2;
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
                                <span
                                  className={`text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md ${day.bg} ${day.text}`}
                                >
                                  {day.short}
                                </span>
                              </td>
                              <td className="px-3 py-3 align-top font-bold text-[#333] tabular-nums whitespace-nowrap">
                                {candidate.session_start_time != null
                                  ? formatTime(candidate.session_start_time)
                                  : "—"}
                              </td>
                              <td className="px-4 py-3">
                                <div className="flex flex-col gap-1.5">
                                  {isPair ? (
                                    <>
                                      {sessions.map((session) => {
                                        const allChecked = sessions.every((s) =>
                                          checkedSessions.has(s.original_block_id),
                                        );
                                        return (
                                          <div
                                            key={session.original_block_id}
                                            className="flex flex-wrap gap-1"
                                          >
                                            {session.class_codes.map((code: string) => (
                                              <span
                                                key={`${session.original_block_id}-${code}`}
                                                className={`rounded px-2 py-0.5 text-[12px] font-semibold transition-colors ${
                                                  allChecked
                                                    ? "bg-[#ffc107] text-[#222]"
                                                    : "bg-[#f0f0f0] text-[#666]"
                                                }`}
                                              >
                                                {code}
                                              </span>
                                            ))}
                                          </div>
                                        );
                                      })}
                                      <label className="flex items-center gap-1.5 cursor-pointer mt-0.5">
                                        <input
                                          type="checkbox"
                                          checked={sessions.every((s) =>
                                            checkedSessions.has(s.original_block_id),
                                          )}
                                          onChange={() => handleSelectAll(candidate)}
                                          className="w-3.5 h-3.5 accent-[#ffc107] cursor-pointer shrink-0"
                                        />
                                        <span className="text-[11px] text-[#999] font-semibold whitespace-nowrap">
                                          selecionar todas
                                        </span>
                                      </label>
                                    </>
                                  ) : (
                                    <>
                                      {sessions.map((session) => {
                                        const checked = checkedSessions.has(
                                          session.original_block_id,
                                        );
                                        return (
                                          <label
                                            key={session.original_block_id}
                                            className="flex items-center gap-1.5 cursor-pointer"
                                          >
                                            <input
                                              type="checkbox"
                                              checked={checked}
                                              onChange={() =>
                                                handleSessionToggle(session.original_block_id)
                                              }
                                              className="w-3.5 h-3.5 accent-[#ffc107] cursor-pointer shrink-0"
                                            />
                                            <div className="flex flex-wrap gap-1">
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
                                          </label>
                                        );
                                      })}
                                      <label className="flex items-center gap-1.5 cursor-pointer mt-0.5">
                                        <input
                                          type="checkbox"
                                          checked={
                                            sessions.length > 0 &&
                                            sessions.every((s) =>
                                              checkedSessions.has(s.original_block_id),
                                            )
                                          }
                                          onChange={() => handleSelectAll(candidate)}
                                          className="w-3.5 h-3.5 accent-[#ffc107] cursor-pointer shrink-0"
                                        />
                                        <span className="text-[11px] text-[#999] font-semibold whitespace-nowrap">
                                          selecionar todas
                                        </span>
                                      </label>
                                    </>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
