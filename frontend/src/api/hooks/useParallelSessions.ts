import { type Dispatch, type SetStateAction, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { ApiError, type ApiRequestError } from "@/types/api";
import { ROUTES } from "@/routes";
import { queryKeys } from "@/api/queryKeys";
import {
  DAY_ORDER,
  type DegreeOption,
  type ParallelBlockNode,
  type ParallelCandidateGraph,
  type ParallelGroup,
  type SuccessResponse,
  type UUID,
  type YearOption,
} from "@/types/parallelSessions";
import { buildAdjacency, isConnectedSelection } from "@/components/parallel/parallelGraph";

function parallelSaveErrorMessage(err: unknown): string {
  const code = err instanceof Error && "code" in err ? (err as ApiRequestError).code : undefined;
  if (code === ApiError.PARALLEL_GROUPS_NOT_CANDIDATES) {
    return "As turmas selecionadas não são candidatas a paralelas.";
  }
  return err instanceof Error ? err.message : "Erro ao guardar";
}

/** A confirmed/draft group enriched with display metadata for the side panel. */
export interface GroupView {
  group: ParallelGroup;
  subjectName: string;
  weekday: string;
  startTime: number;
  blocks: { blockId: UUID; type: string; codes: string[] }[];
}

function groupSignature(groups: ParallelGroup[]): string {
  return groups
    .map((g) => `${g.candidateGroupId}:${[...g.blockIds].sort().join(",")}`)
    .sort()
    .join("|");
}

export interface UseParallelSessionsReturn {
  degrees: DegreeOption[];
  loadingDegrees: boolean;
  degreesError: string | null;
  selectedDegree: DegreeOption | null;

  loadingYears: boolean;
  yearsError: string | null;
  selectedYearIds: Set<UUID>;
  yearsWithCandidates: YearOption[];

  loadingCandidates: boolean;
  candidatesError: string | null;
  /** Candidate graphs visible under the current degree/year filter. */
  visibleGraphs: ParallelCandidateGraph[];

  /** Blocks already assigned to a draft/confirmed group (locked in the graph). */
  assignedBlockIds: Set<UUID>;
  /** Per-component in-progress selection. */
  selectionByGroup: Record<UUID, Set<UUID>>;
  /** Whether the current selection for a component is a valid (connected, ≥2) group. */
  isSelectionValid: (candidateGroupId: UUID) => boolean;

  groupViewsBySubject: Map<string, GroupView[]>;
  savedGroupIds: Set<string>;

  saving: boolean;
  saveStatus: { type: "success" | "error"; message: string } | null;
  isDirty: boolean;

  showUnsavedModal: boolean;
  setShowUnsavedModal: Dispatch<SetStateAction<boolean>>;
  showResetModal: boolean;
  setShowResetModal: Dispatch<SetStateAction<boolean>>;

  handleDegreeClick: (degree: DegreeOption) => void;
  handleYearToggle: (yearId: UUID) => void;
  handleToggleNode: (candidateGroupId: UUID, blockId: UUID) => void;
  handleCreateGroup: (candidateGroupId: UUID) => void;
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

  const [restoredState] = useState<{ degreeId: string; yearIds: string[] } | null>(() => {
    const raw = sessionStorage.getItem(`parallelClasses-${projectId ?? ""}`);
    if (!raw) return null;
    sessionStorage.removeItem(`parallelClasses-${projectId ?? ""}`);
    try {
      return JSON.parse(raw) as { degreeId: string; yearIds: string[] };
    } catch {
      return null;
    }
  });

  const [graphs, setGraphs] = useState<ParallelCandidateGraph[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [candidatesError, setCandidatesError] = useState<string | null>(null);

  const [selectedDegree, setSelectedDegree] = useState<DegreeOption | null>(null);
  const [degreeYears, setDegreeYears] = useState<YearOption[]>([]);
  const [loadingYears, setLoadingYears] = useState(false);
  const [yearsError, setYearsError] = useState<string | null>(null);
  const [selectedYearIds, setSelectedYearIds] = useState<Set<UUID>>(new Set());

  const [groups, setGroups] = useState<ParallelGroup[]>([]);
  const [savedSnapshot, setSavedSnapshot] = useState<ParallelGroup[]>([]);
  const [selectionByGroup, setSelectionByGroup] = useState<Record<UUID, Set<UUID>>>({});

  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [showUnsavedModal, setShowUnsavedModal] = useState(false);
  const [showResetModal, setShowResetModal] = useState(false);
  const pendingRoute = useRef<string>("");

  const projectIdNum = useMemo(() => Number(projectId), [projectId]);

  // -- Load all candidate graphs ----------------------------------------
  useEffect(() => {
    if (!projectId || Number.isNaN(projectIdNum)) return;

    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingCandidates(true);
    setCandidatesError(null);

    api
      .get<SuccessResponse<ParallelCandidateGraph[]>>(
        `/api/projects/${projectIdNum}/parallel-blocks/candidates`,
      )
      .then((res) => {
        if (cancelled) return;
        const loaded = res.data;
        setGraphs(loaded);

        // Reconstruct confirmed groups straight from the payload: every node
        // carries the confirmed_group_id it is saved under.
        const byConfirmed = new Map<string, ParallelGroup>();
        for (const g of loaded) {
          for (const node of g.nodes) {
            if (!node.confirmed_group_id) continue;
            const key = node.confirmed_group_id;
            let grp = byConfirmed.get(key);
            if (!grp) {
              grp = {
                id: key,
                candidateGroupId: g.candidate_group_id,
                blockIds: [],
                confirmed: true,
              };
              byConfirmed.set(key, grp);
            }
            grp.blockIds.push(node.original_block_id);
          }
        }
        const confirmed = [...byConfirmed.values()];
        setGroups(confirmed);
        setSavedSnapshot(confirmed);
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
  }, [projectId, projectIdNum]);

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

  const loadingDegrees = loadingCandidates;
  const degreesError = candidatesError;

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

  // -- Year numbers for the selected degree -----------------------------
  useEffect(() => {
    if (!selectedDegree || !projectId || Number.isNaN(projectIdNum)) return;

    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoadingYears(true);
    setYearsError(null);
    setDegreeYears([]);

    api
      .get<SuccessResponse<{ years: YearOption[] }>>(
        `/api/projects/${projectIdNum}/degrees/${selectedDegree.id}`,
      )
      .then((res) => {
        if (cancelled) return;
        setDegreeYears(res.data.years);
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

  // Graphs that belong to the selected degree.
  const degreeGraphs = useMemo(
    () =>
      selectedDegree
        ? graphs.filter((g) => g.subject.years.some((y) => y.degree.id === selectedDegree.id))
        : [],
    [graphs, selectedDegree],
  );

  // Year rows of the selected degree that actually carry candidate blocks.
  const yearsWithCandidates = useMemo(() => {
    const yearIdsWithData = new Set<UUID>();
    for (const g of degreeGraphs) {
      for (const node of g.nodes) {
        for (const yid of node.year_ids) yearIdsWithData.add(yid);
      }
    }
    return degreeYears.filter((y) => yearIdsWithData.has(y.id)).sort((a, b) => a.number - b.number);
  }, [degreeGraphs, degreeYears]);

  // Default year selection to all years with candidates (or the restored set).
  const yearsKey = useMemo(
    () => yearsWithCandidates.map((y) => y.id).join(","),
    [yearsWithCandidates],
  );
  useEffect(() => {
    if (yearsWithCandidates.length === 0) return;
    const restored =
      restoredState?.degreeId === selectedDegree?.id ? restoredState?.yearIds : undefined;
    const allowed = new Set(yearsWithCandidates.map((y) => y.id));
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelectedYearIds(
      restored
        ? new Set(restored.filter((id) => allowed.has(id)))
        : new Set(yearsWithCandidates.map((y) => y.id)),
    );
    // Re-run when the set of candidate years changes (e.g. degree switch).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [yearsKey]);

  const selectedYearIdSet = selectedYearIds;

  // Visible graphs: belong to the degree and touch a selected year.
  const visibleGraphs = useMemo(() => {
    if (selectedYearIdSet.size === 0) return degreeGraphs;
    return degreeGraphs.filter((g) =>
      g.nodes.some((node) => node.year_ids.some((yid) => selectedYearIdSet.has(yid))),
    );
  }, [degreeGraphs, selectedYearIdSet]);

  // -- Lookups ----------------------------------------------------------
  const nodeIndex = useMemo(() => {
    const map = new Map<UUID, { node: ParallelBlockNode; graph: ParallelCandidateGraph }>();
    for (const g of graphs) {
      for (const node of g.nodes) map.set(node.original_block_id, { node, graph: g });
    }
    return map;
  }, [graphs]);

  const adjacencyByGroup = useMemo(() => {
    const map = new Map<UUID, Map<UUID, Set<UUID>>>();
    for (const g of graphs) map.set(g.candidate_group_id, buildAdjacency(g.edges));
    return map;
  }, [graphs]);

  const assignedBlockIds = useMemo(() => new Set(groups.flatMap((g) => g.blockIds)), [groups]);

  const isSelectionValid = (candidateGroupId: UUID): boolean => {
    const selection = selectionByGroup[candidateGroupId];
    if (!selection || selection.size < 2) return false;
    const adj = adjacencyByGroup.get(candidateGroupId);
    if (!adj) return false;
    return isConnectedSelection(selection, adj);
  };

  // -- Side-panel group views -------------------------------------------
  const groupViewsBySubject = useMemo(() => {
    const views: GroupView[] = groups.map((group) => {
      const blocks = group.blockIds
        .map((id) => nodeIndex.get(id))
        .filter((e): e is { node: ParallelBlockNode; graph: ParallelCandidateGraph } => e != null);
      const first = blocks[0];
      return {
        group,
        subjectName: first?.graph.subject.name ?? "Disciplina",
        weekday: first?.graph.weekday ?? "",
        startTime: first?.node.session.start_time ?? 0,
        blocks: blocks.map((e) => ({
          blockId: e.node.original_block_id,
          type: e.node.session.type,
          codes: e.node.classes.map((c) => c.code),
        })),
      };
    });

    const map = new Map<string, GroupView[]>();
    for (const view of views) {
      const list = map.get(view.subjectName);
      if (list) list.push(view);
      else map.set(view.subjectName, [view]);
    }
    for (const list of map.values()) {
      list.sort(
        (a, b) =>
          (DAY_ORDER[a.weekday] ?? 99) - (DAY_ORDER[b.weekday] ?? 99) || a.startTime - b.startTime,
      );
    }
    return map;
  }, [groups, nodeIndex]);

  const savedGroupIds = useMemo(() => new Set(savedSnapshot.map((g) => g.id)), [savedSnapshot]);

  const savedSignature = useMemo(() => groupSignature(savedSnapshot), [savedSnapshot]);
  const currentSignature = useMemo(() => groupSignature(groups), [groups]);
  const isDirty = savedSignature !== currentSignature;

  const backRoute = ROUTES.SCHEDULE.replace(":projectId", projectId ?? "");

  // -- Handlers ---------------------------------------------------------
  const handleDegreeClick = (degree: DegreeOption) => {
    setSelectedDegree((prev) => (prev?.id === degree.id ? prev : degree));
    setSelectionByGroup({});
  };

  const handleYearToggle = (yearId: UUID) => {
    setSelectedYearIds((prev) => {
      const next = new Set(prev);
      if (next.has(yearId)) next.delete(yearId);
      else next.add(yearId);
      return next;
    });
  };

  const handleToggleNode = (candidateGroupId: UUID, blockId: UUID) => {
    if (assignedBlockIds.has(blockId)) return;
    setSelectionByGroup((prev) => {
      const current = new Set(prev[candidateGroupId] ?? []);
      if (current.has(blockId)) current.delete(blockId);
      else current.add(blockId);
      return { ...prev, [candidateGroupId]: current };
    });
  };

  const handleCreateGroup = (candidateGroupId: UUID) => {
    const selection = selectionByGroup[candidateGroupId];
    if (!selection || selection.size < 2) return;
    const adj = adjacencyByGroup.get(candidateGroupId);
    if (!adj || !isConnectedSelection(selection, adj)) return;
    const blockIds = [...selection];
    setGroups((prev) => [
      ...prev,
      { id: crypto.randomUUID(), candidateGroupId, blockIds, confirmed: false },
    ]);
    setSelectionByGroup((prev) => ({ ...prev, [candidateGroupId]: new Set() }));
  };

  const handleRemoveGroup = (groupId: string) => {
    setGroups((prev) => prev.filter((g) => g.id !== groupId));
  };

  const handleBack = () => {
    pendingRoute.current = backRoute;
    if (isDirty) setShowUnsavedModal(true);
    else void navigate(backRoute);
  };

  const handleNavigateHome = () => {
    pendingRoute.current = ROUTES.HOME;
    if (isDirty) setShowUnsavedModal(true);
    else void navigate(ROUTES.HOME);
  };

  const performSave = async () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    const payload = groups
      .filter((g) => g.blockIds.length >= 2)
      .map((g) => ({ candidate_group_id: g.candidateGroupId, classes: g.blockIds }));
    await api.post(`/api/projects/${projectIdNum}/parallel-blocks/groups/`, { groups: payload });
    sessionStorage.setItem(
      `parallelClasses-${projectId}`,
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
      .post(`/api/projects/${projectIdNum}/parallel-blocks/groups/`, { groups: [] })
      .then(() => {
        void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
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
      setSavedSnapshot(groups.map((g) => ({ ...g, confirmed: true })));
      setSaveStatus({ type: "success", message: "Guardado com sucesso" });
    } catch (err) {
      setSaveStatus({ type: "error", message: parallelSaveErrorMessage(err) });
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
      void navigate(pendingRoute.current || backRoute);
    } catch (err) {
      setShowUnsavedModal(false);
      setSaveStatus({ type: "error", message: parallelSaveErrorMessage(err) });
    } finally {
      setSaving(false);
    }
  };

  return {
    degrees,
    loadingDegrees,
    degreesError,
    selectedDegree,
    loadingYears,
    yearsError,
    selectedYearIds,
    yearsWithCandidates,
    loadingCandidates,
    candidatesError,
    visibleGraphs,
    assignedBlockIds,
    selectionByGroup,
    isSelectionValid,
    groupViewsBySubject,
    savedGroupIds,
    saving,
    saveStatus,
    isDirty,
    showUnsavedModal,
    setShowUnsavedModal,
    showResetModal,
    setShowResetModal,
    handleDegreeClick,
    handleYearToggle,
    handleToggleNode,
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
