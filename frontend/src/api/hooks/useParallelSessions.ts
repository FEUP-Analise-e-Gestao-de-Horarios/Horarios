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
  if (code === ApiError.PARALLEL_GROUPS_INVALID_CANDIDATES) {
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
  /** Whether all still-unassigned nodes of a component form a valid group. */
  canGroupAll: (candidateGroupId: UUID) => boolean;

  groupViewsBySubject: Map<string, GroupView[]>;
  savedGroupIds: Set<string>;

  /** True while any create/delete request is in flight. */
  saving: boolean;
  saveStatus: { type: "success" | "error"; message: string } | null;

  showResetModal: boolean;
  setShowResetModal: Dispatch<SetStateAction<boolean>>;

  handleDegreeClick: (degree: DegreeOption) => void;
  handleYearToggle: (yearId: UUID) => void;
  handleYearSelect: (yearId: UUID) => void;
  handleToggleNode: (candidateGroupId: UUID, blockId: UUID) => void;
  /** Create a group from the current selection; returns its id, or null if invalid. */
  handleCreateGroup: (candidateGroupId: UUID) => UUID | null;
  /** Group all still-free nodes of a component; returns its id, or null if invalid. */
  handleGroupAll: (candidateGroupId: UUID) => UUID | null;
  handleRemoveGroup: (groupId: string) => void;
  handleBack: () => void;
  handleNavigateHome: () => void;
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
  // Remembers the last year picked per degree, so returning to a degree restores it.
  const yearByDegree = useRef<Record<string, UUID>>({});

  const [groups, setGroups] = useState<ParallelGroup[]>([]);
  const [selectionByGroup, setSelectionByGroup] = useState<Record<UUID, Set<UUID>>>({});

  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [showResetModal, setShowResetModal] = useState(false);

  // In-flight create requests, keyed by local group id, resolving to the
  // backend group id (or null on failure). A delete can await one so it can
  // remove a group whose create round-trip has not landed yet.
  const pendingCreates = useRef<Map<string, Promise<UUID | null>>>(new Map());
  // Count of outstanding save requests, to drive the `saving` flag.
  const inFlight = useRef(0);

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
                serverId: key,
                candidateGroupId: g.candidate_group_id,
                blockIds: [],
                confirmed: true,
              };
              byConfirmed.set(key, grp);
            }
            grp.blockIds.push(node.original_block_id);
          }
        }
        setGroups([...byConfirmed.values()]);
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
        for (const cls of node.classes) yearIdsWithData.add(cls.year_id);
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

  // Block ids of a component still free to be grouped (not already assigned).
  const unassignedBlockIds = (candidateGroupId: UUID): UUID[] => {
    const graph = graphs.find((g) => g.candidate_group_id === candidateGroupId);
    if (!graph) return [];
    return graph.nodes.map((n) => n.original_block_id).filter((id) => !assignedBlockIds.has(id));
  };

  const canGroupAll = (candidateGroupId: UUID): boolean => {
    const blockIds = unassignedBlockIds(candidateGroupId);
    if (blockIds.length < 2) return false;
    const adj = adjacencyByGroup.get(candidateGroupId);
    if (!adj) return false;
    return isConnectedSelection(new Set(blockIds), adj);
  };

  // -- Side-panel group views -------------------------------------------
  const groupViewsBySubject = useMemo(() => {
    const views: GroupView[] = [];
    for (const group of groups) {
      const blocks = group.blockIds
        .map((id) => nodeIndex.get(id))
        .filter((e): e is { node: ParallelBlockNode; graph: ParallelCandidateGraph } => e != null);

      // Mirror the candidate list: only show groups whose blocks touch a
      // selected year (all years when none is selected).
      if (
        selectedYearIdSet.size > 0 &&
        !blocks.some((e) => e.node.classes.some((c) => selectedYearIdSet.has(c.year_id)))
      ) {
        continue;
      }

      const first = blocks[0];
      views.push({
        group,
        subjectName: first?.graph.subject.name ?? "Disciplina",
        weekday: first?.graph.weekday ?? "",
        startTime: first?.node.session.start_time ?? 0,
        blocks: blocks.map((e) => ({
          blockId: e.node.original_block_id,
          type: e.node.session.type,
          codes: e.node.classes.map((c) => c.code),
        })),
      });
    }

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
  }, [groups, nodeIndex, selectedYearIdSet]);

  // Groups already persisted on the server (a create round-trip has landed).
  const savedGroupIds = useMemo(
    () => new Set(groups.filter((g) => g.confirmed).map((g) => g.id)),
    [groups],
  );

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

  // Single-year selection for the pill selector: replace the whole set and
  // remember it for the current degree.
  const handleYearSelect = (yearId: UUID) => {
    if (selectedDegree) yearByDegree.current[selectedDegree.id] = yearId;
    setSelectedYearIds(new Set([yearId]));
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

  // -- Per-action persistence -------------------------------------------
  // Every create/remove hits the backend immediately with an optimistic UI
  // update that rolls back if the request fails.
  const beginRequest = () => {
    inFlight.current += 1;
    setSaving(true);
    setSaveStatus(null);
  };
  const endRequest = () => {
    inFlight.current = Math.max(0, inFlight.current - 1);
    if (inFlight.current === 0) setSaving(false);
  };

  // POST a freshly-created group; on success adopt its backend id, on failure
  // drop the optimistic card. Registers the round-trip so a racing delete can
  // await the resulting id.
  const persistCreate = (localId: string, candidateGroupId: UUID, blockIds: UUID[]): void => {
    beginRequest();
    const request = api
      .post<SuccessResponse<{ group_id: UUID }>>(
        `/api/projects/${projectIdNum}/parallel-blocks/groups/`,
        { candidate_group_id: candidateGroupId, block_ids: blockIds },
      )
      .then((res): UUID | null => {
        const serverId = res.data.group_id;
        setGroups((prev) =>
          prev.map((g) => (g.id === localId ? { ...g, serverId, confirmed: true } : g)),
        );
        void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        setSaveStatus({ type: "success", message: "Guardado" });
        return serverId;
      })
      .catch((err: unknown): null => {
        setGroups((prev) => prev.filter((g) => g.id !== localId));
        setSaveStatus({ type: "error", message: parallelSaveErrorMessage(err) });
        return null;
      })
      .finally(() => {
        pendingCreates.current.delete(localId);
        endRequest();
      });
    pendingCreates.current.set(localId, request);
  };

  // DELETE a removed group; waits for an in-flight create so a just-created
  // group can still be deleted. Restores the card if the request fails.
  const persistDelete = async (group: ParallelGroup): Promise<void> => {
    let serverId = group.serverId;
    if (!serverId) {
      const pending = pendingCreates.current.get(group.id);
      serverId = pending ? await pending : null;
    }
    // Never persisted (its create failed, or is still gone): the optimistic
    // removal already matches the server.
    if (!serverId) return;

    beginRequest();
    try {
      await api.delete(`/api/projects/${projectIdNum}/parallel-blocks/groups/${serverId}`);
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
      setSaveStatus({ type: "success", message: "Guardado" });
    } catch (err) {
      const restored: ParallelGroup = { ...group, serverId, confirmed: true };
      setGroups((prev) => (prev.some((g) => g.id === group.id) ? prev : [...prev, restored]));
      setSaveStatus({ type: "error", message: parallelSaveErrorMessage(err) });
    } finally {
      endRequest();
    }
  };

  const handleCreateGroup = (candidateGroupId: UUID): UUID | null => {
    const selection = selectionByGroup[candidateGroupId];
    if (!selection || selection.size < 2) return null;
    const adj = adjacencyByGroup.get(candidateGroupId);
    if (!adj || !isConnectedSelection(selection, adj)) return null;
    const blockIds = [...selection];
    const id = crypto.randomUUID();
    setGroups((prev) => [
      ...prev,
      { id, serverId: null, candidateGroupId, blockIds, confirmed: false },
    ]);
    setSelectionByGroup((prev) => ({ ...prev, [candidateGroupId]: new Set() }));
    persistCreate(id, candidateGroupId, blockIds);
    return id;
  };

  // Group every still-unassigned node of a component in one action.
  const handleGroupAll = (candidateGroupId: UUID): UUID | null => {
    const blockIds = unassignedBlockIds(candidateGroupId);
    if (blockIds.length < 2) return null;
    const adj = adjacencyByGroup.get(candidateGroupId);
    if (!adj || !isConnectedSelection(new Set(blockIds), adj)) return null;
    const id = crypto.randomUUID();
    setGroups((prev) => [
      ...prev,
      { id, serverId: null, candidateGroupId, blockIds, confirmed: false },
    ]);
    setSelectionByGroup((prev) => ({ ...prev, [candidateGroupId]: new Set() }));
    persistCreate(id, candidateGroupId, blockIds);
    return id;
  };

  const handleRemoveGroup = (groupId: string) => {
    const group = groups.find((g) => g.id === groupId);
    if (!group) return;
    setGroups((prev) => prev.filter((g) => g.id !== groupId));
    void persistDelete(group);
  };

  // Remember the current degree/year so returning to the page restores it.
  const rememberView = () => {
    if (!projectId) return;
    sessionStorage.setItem(
      `parallelClasses-${projectId}`,
      JSON.stringify({ degreeId: selectedDegree?.id, yearIds: [...selectedYearIds] }),
    );
  };

  const handleBack = () => {
    rememberView();
    void navigate(backRoute);
  };

  const handleNavigateHome = () => {
    rememberView();
    void navigate(ROUTES.HOME);
  };

  const handleReset = () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    setShowResetModal(true);
  };

  const confirmReset = () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    rememberView();
    api
      .delete(`/api/projects/${projectIdNum}/parallel-blocks/groups/`)
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
    canGroupAll,
    groupViewsBySubject,
    savedGroupIds,
    saving,
    saveStatus,
    showResetModal,
    setShowResetModal,
    handleDegreeClick,
    handleYearToggle,
    handleYearSelect,
    handleToggleNode,
    handleCreateGroup,
    handleGroupAll,
    handleRemoveGroup,
    handleBack,
    handleNavigateHome,
    handleReset,
    confirmReset,
  };
}
