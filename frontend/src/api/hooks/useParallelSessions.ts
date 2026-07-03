import { type Dispatch, type SetStateAction, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
  type UnconfirmedDegree,
  type UnconfirmedYear,
  type UUID,
  type YearOption,
} from "@/types/parallelSessions";
import { buildAdjacency, isConnectedSelection } from "@/components/parallel/parallelGraph";

/** How long a confirmed-deleted card releases, fades, and collapses out before
 * it is dropped from the list. Kept just above the CSS leave duration (500ms)
 * so the row has finished animating away before it unmounts. */
const GROUP_LEAVE_MS = 520;

/** Minimum time a card holds in its pending (shifted + glowing) state before it
 * releases, so a fast backend still lets the create/delete animation play out
 * fully instead of snapping. Matches the CSS glow duration (0.55s). */
const GROUP_MIN_HOLD_MS = 550;

const delay = (ms: number): Promise<void> =>
  new Promise((resolve) => window.setTimeout(resolve, ms));

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

  /** True while any create/delete request is in flight. */
  saving: boolean;
  saveStatus: { type: "success" | "error"; message: string } | null;

  showResetModal: boolean;
  setShowResetModal: Dispatch<SetStateAction<boolean>>;

  /** Subject ids the user has marked reviewed/confirmed. */
  confirmedSubjectIds: Set<UUID>;
  /** Year ids all of whose subjects are confirmed (across every degree). */
  confirmedYearIds: Set<UUID>;
  /** Degree ids all of whose years are confirmed. */
  confirmedDegreeIds: Set<UUID>;
  /** Confirm a subject; resolves false (rolled back) if the request was rejected. */
  confirmSubject: (subjectId: UUID) => Promise<boolean>;
  unconfirmSubject: (subjectId: UUID) => void;
  /** True when every year with candidates (all degrees) is confirmed. */
  allYearsConfirmed: boolean;
  /** Degrees with unconfirmed years, for the finish prompt. */
  unconfirmedByDegree: UnconfirmedDegree[];

  showFinishModal: boolean;
  setShowFinishModal: Dispatch<SetStateAction<boolean>>;
  /** Shown when a confirm was rejected as stale; the list has been refetched. */
  /** Which confirm was rejected as stale (drives the prompt copy), or null. */
  staleConfirmScope: "subject" | "all" | null;
  setStaleConfirmScope: Dispatch<SetStateAction<"subject" | "all" | null>>;
  /** Terminar: mark done and leave if all confirmed, else open the finish prompt. */
  handleFinish: () => void;
  /** Confirm everything, mark the step done, then leave for the schedule. */
  finishAndConfirmAll: () => void;
  /** Mark the step done and leave without confirming the rest (won't be asked again). */
  finishContinue: () => void;
  /** Leave for the schedule without marking the step done (asked again next time). */
  finishLater: () => void;

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

  const projectIdNum = Number(projectId);
  const candidatesEnabled = Boolean(projectId) && !Number.isNaN(projectIdNum);
  const candidatesQuery = useQuery({
    queryKey: queryKeys.projects.parallelCandidates(String(projectIdNum)),
    queryFn: async () => {
      const res = await api.get<SuccessResponse<ParallelCandidateGraph[]>>(
        `/api/projects/${projectIdNum}/parallel-blocks/candidates`,
      );
      return res.data;
    },
    enabled: candidatesEnabled,
    // The graph structure is stable for a session; groups are mutated locally
    // and persisted separately, so never auto-refetch this payload.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  const graphs = useMemo(() => candidatesQuery.data ?? [], [candidatesQuery.data]);
  const loadingCandidates = candidatesQuery.isLoading;
  const candidatesError = candidatesQuery.error
    ? candidatesQuery.error instanceof Error
      ? candidatesQuery.error.message
      : "Failed to load parallel candidates"
    : null;

  const [selectedDegree, setSelectedDegree] = useState<DegreeOption | null>(null);
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
  const [showFinishModal, setShowFinishModal] = useState(false);
  // Set when a confirm is rejected because the candidates changed under the
  // user; the list is refetched and this prompts a re-check. The scope drives
  // the prompt copy: a single subject vs. the finish-all action.
  const [staleConfirmScope, setStaleConfirmScope] = useState<"subject" | "all" | null>(null);

  // Subjects the user has marked reviewed. Seeded from the payload (a subject is
  // confirmed when all its candidates are) and then mutated optimistically.
  const [confirmedSubjectIds, setConfirmedSubjectIds] = useState<Set<UUID>>(new Set());

  // In-flight create requests, keyed by local group id, resolving to the
  // backend group id (or null on failure). A delete can await one so it can
  // remove a group whose create round-trip has not landed yet.
  const pendingCreates = useRef<Map<string, Promise<UUID | null>>>(new Map());
  // Count of outstanding save requests, to drive the `saving` flag.
  const inFlight = useRef(0);

  // -- Seed confirmed groups from the loaded candidate payload ----------
  // Runs once per project once the query resolves. Every node carries the
  // confirmed_group_id it is saved under, so confirmed groups are fully
  // derivable from the payload; drafts live only in local state.
  const seededProjectRef = useRef<string | null>(null);
  useEffect(() => {
    if (loadingCandidates || !candidatesQuery.data) return;
    const seedKey = String(projectIdNum);
    if (seededProjectRef.current === seedKey) return;
    seededProjectRef.current = seedKey;

    const byConfirmed = new Map<string, ParallelGroup>();
    const confirmedSubjects = new Set<UUID>();
    for (const g of candidatesQuery.data) {
      if (g.subject.confirmed) confirmedSubjects.add(g.subject.id);
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
            status: "saved",
          };
          byConfirmed.set(key, grp);
        }
        grp.blockIds.push(node.original_block_id);
      }
    }
    setGroups([...byConfirmed.values()]);
    setConfirmedSubjectIds(confirmedSubjects);
  }, [candidatesQuery.data, loadingCandidates, projectIdNum]);

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

  // -- Confirmation roll-up (subject -> year -> degree) -----------------
  // A year is confirmed once every subject taught in it is confirmed; a degree
  // once every one of its years is. All computed across the whole payload (every
  // degree), so the finish check can span degrees the user never opened.

  // year id -> the subject ids that have candidates in that year.
  const subjectsByYear = useMemo(() => {
    const map = new Map<UUID, Set<UUID>>();
    for (const g of graphs) {
      for (const y of g.subject.years) {
        let set = map.get(y.id);
        if (!set) {
          set = new Set();
          map.set(y.id, set);
        }
        set.add(g.subject.id);
      }
    }
    return map;
  }, [graphs]);

  // degree -> its year rows (id + number), across the whole payload.
  const yearsByDegree = useMemo(() => {
    const map = new Map<UUID, { degree: DegreeOption; years: Map<UUID, number> }>();
    for (const g of graphs) {
      for (const y of g.subject.years) {
        let entry = map.get(y.degree.id);
        if (!entry) {
          entry = {
            degree: { id: y.degree.id, name: y.degree.name, acronym: y.degree.acronym },
            years: new Map(),
          };
          map.set(y.degree.id, entry);
        }
        entry.years.set(y.id, y.number);
      }
    }
    return map;
  }, [graphs]);

  const confirmedYearIds = useMemo(() => {
    const set = new Set<UUID>();
    for (const [yearId, subjectIds] of subjectsByYear) {
      if (subjectIds.size > 0 && [...subjectIds].every((id) => confirmedSubjectIds.has(id))) {
        set.add(yearId);
      }
    }
    return set;
  }, [subjectsByYear, confirmedSubjectIds]);

  const confirmedDegreeIds = useMemo(() => {
    const set = new Set<UUID>();
    for (const [degreeId, { years }] of yearsByDegree) {
      if (years.size > 0 && [...years.keys()].every((id) => confirmedYearIds.has(id))) {
        set.add(degreeId);
      }
    }
    return set;
  }, [yearsByDegree, confirmedYearIds]);

  // subject id -> acronym, for labelling the pending rows in the finish prompt.
  const subjectAcronymById = useMemo(() => {
    const map = new Map<UUID, string>();
    for (const g of graphs) map.set(g.subject.id, g.subject.acronym);
    return map;
  }, [graphs]);

  // Degrees with at least one unconfirmed year, for the finish prompt. Each
  // pending year carries the acronyms of the subjects still unconfirmed in it.
  const unconfirmedByDegree = useMemo<UnconfirmedDegree[]>(() => {
    const out: UnconfirmedDegree[] = [];
    for (const { degree, years } of yearsByDegree.values()) {
      const pending: UnconfirmedYear[] = [...years.entries()]
        .filter(([yearId]) => !confirmedYearIds.has(yearId))
        .map(([id, number]) => {
          const subjects = [...(subjectsByYear.get(id) ?? [])]
            .filter((sid) => !confirmedSubjectIds.has(sid))
            .map((sid) => ({ id: sid, acronym: subjectAcronymById.get(sid) ?? "?" }))
            .sort((a, b) => a.acronym.localeCompare(b.acronym));
          return { id, number, subjects };
        })
        .sort((a, b) => a.number - b.number);
      if (pending.length > 0) out.push({ degree, years: pending });
    }
    out.sort((a, b) => a.degree.acronym.localeCompare(b.degree.acronym));
    return out;
  }, [yearsByDegree, confirmedYearIds, subjectsByYear, confirmedSubjectIds, subjectAcronymById]);

  const allYearsConfirmed = unconfirmedByDegree.length === 0;

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
    // Hold the "added" animation for at least GROUP_MIN_HOLD_MS even if the POST
    // returns sooner, so the card's slide-and-glow always plays out.
    const request = Promise.all([
      api.post<SuccessResponse<{ group_id: UUID }>>(
        `/api/projects/${projectIdNum}/parallel-blocks/groups/`,
        { candidate_group_id: candidateGroupId, block_ids: blockIds },
      ),
      delay(GROUP_MIN_HOLD_MS),
    ])
      .then(([res]): UUID | null => {
        const serverId = res.data.group_id;
        // Adopt the backend id and settle to "saved" — unless a delete already
        // moved this card to "deleting" while the create was in flight, in
        // which case keep that status so the delete can carry on.
        setGroups((prev) =>
          prev.map((g) =>
            g.id === localId
              ? { ...g, serverId, status: g.status === "creating" ? "saved" : g.status }
              : g,
          ),
        );
        void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
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

  // DELETE a group the user asked to remove (it is already showing its
  // "deleting" state). Waits for an in-flight create so a just-created group
  // can still be deleted. Only once the server confirms does the card collapse
  // out and get dropped; a failure settles it back to "saved".
  const persistDelete = async (group: ParallelGroup): Promise<void> => {
    beginRequest();
    try {
      let serverId = group.serverId;
      if (!serverId) {
        const pending = pendingCreates.current.get(group.id);
        serverId = pending ? await pending : null;
      }
      // Its create never landed (failed / nothing on the server): just drop it.
      if (!serverId) {
        setGroups((prev) => prev.filter((g) => g.id !== group.id));
        return;
      }

      // Hold the "removing" animation for at least GROUP_MIN_HOLD_MS even if the
      // DELETE returns sooner, so the card's slide-and-glow always plays out.
      await Promise.all([
        api.delete(`/api/projects/${projectIdNum}/parallel-blocks/groups/${serverId}`),
        delay(GROUP_MIN_HOLD_MS),
      ]);
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });

      // Confirmed: play the collapse-out, then drop the row once it settles so
      // the remaining cards slide up into its place.
      setGroups((prev) => prev.map((g) => (g.id === group.id ? { ...g, status: "leaving" } : g)));
      window.setTimeout(() => {
        setGroups((prev) => prev.filter((g) => g.id !== group.id));
      }, GROUP_LEAVE_MS);
    } catch (err) {
      // Failed: settle the card back to its saved resting state (releases the
      // red border and rightward shift).
      setGroups((prev) => prev.map((g) => (g.id === group.id ? { ...g, status: "saved" } : g)));
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
      { id, serverId: null, candidateGroupId, blockIds, status: "creating" },
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
      { id, serverId: null, candidateGroupId, blockIds, status: "creating" },
    ]);
    setSelectionByGroup((prev) => ({ ...prev, [candidateGroupId]: new Set() }));
    persistCreate(id, candidateGroupId, blockIds);
    return id;
  };

  const handleRemoveGroup = (groupId: string) => {
    const group = groups.find((g) => g.id === groupId);
    if (!group) return;
    // Already on its way out — don't restart the delete.
    if (group.status === "deleting" || group.status === "leaving") return;
    // Flag the card for deletion (red border + rightward shift); the row is only
    // dropped once the server confirms, inside persistDelete.
    setGroups((prev) => prev.map((g) => (g.id === groupId ? { ...g, status: "deleting" } : g)));
    void persistDelete(group);
  };

  // -- Confirmation persistence -----------------------------------------
  // Confirm/unconfirm a whole subject: the server resolves the subject's
  // current candidate ids and stores/removes them. Optimistic, rolling back on
  // failure. A pure "reviewed" flag — independent of whether groups were made.
  // Resolves true when the confirm landed, false when it was rejected (rolled
  // back) — so the caller can undo any optimistic UI (e.g. the auto-jump).
  const confirmSubject = (subjectId: UUID): Promise<boolean> => {
    if (!projectId || Number.isNaN(projectIdNum)) return Promise.resolve(false);
    // The candidate ids we currently show for this subject; the server rejects
    // the confirm if this no longer matches its live set.
    const candidateGroupIds = graphs
      .filter((g) => g.subject.id === subjectId)
      .map((g) => g.candidate_group_id);
    setConfirmedSubjectIds((prev) => new Set(prev).add(subjectId));
    beginRequest();
    return api
      .post(`/api/projects/${projectIdNum}/parallel-blocks/confirmations/`, {
        subject_id: subjectId,
        candidate_group_ids: candidateGroupIds,
      })
      .then(() => true)
      .catch((err: unknown) => {
        setConfirmedSubjectIds((prev) => {
          const next = new Set(prev);
          next.delete(subjectId);
          return next;
        });
        const code =
          err instanceof Error && "code" in err ? (err as ApiRequestError).code : undefined;
        if (code === ApiError.PARALLEL_CONFIRMATION_STALE) {
          // The list is out of date: pull a fresh copy and tell the user to recheck.
          void queryClient.invalidateQueries({
            queryKey: queryKeys.projects.parallelCandidates(String(projectIdNum)),
          });
          setStaleConfirmScope("subject");
        } else {
          setSaveStatus({
            type: "error",
            message: err instanceof Error ? err.message : "Erro ao confirmar",
          });
        }
        return false;
      })
      .finally(endRequest);
  };

  const unconfirmSubject = (subjectId: UUID) => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    setConfirmedSubjectIds((prev) => {
      const next = new Set(prev);
      next.delete(subjectId);
      return next;
    });
    beginRequest();
    api
      .delete(`/api/projects/${projectIdNum}/parallel-blocks/confirmations/${subjectId}`)
      .catch((err: unknown) => {
        setConfirmedSubjectIds((prev) => new Set(prev).add(subjectId));
        setSaveStatus({
          type: "error",
          message: err instanceof Error ? err.message : "Erro ao repor",
        });
      })
      .finally(endRequest);
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

  // Mark this project's parallel-selection step done, then leave for the
  // schedule. Set on every Terminar exit (confirmed or not) so the home card
  // stops routing back here; only leaves once the write lands.
  const markSelectedAndLeave = () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    beginRequest();
    api
      .post(`/api/projects/${projectIdNum}/parallel-blocks/finish`, {})
      .then(() => {
        // Refresh the project list so ProjectCard sees the updated flag.
        void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        setShowFinishModal(false);
        rememberView();
        void navigate(backRoute);
      })
      .catch((err: unknown) => {
        setSaveStatus({
          type: "error",
          message: err instanceof Error ? err.message : "Erro ao terminar",
        });
      })
      .finally(endRequest);
  };

  // Finish: mark done and leave when every year (across all degrees) is
  // confirmed, otherwise open the prompt listing the years still pending.
  const handleFinish = () => {
    if (allYearsConfirmed) {
      markSelectedAndLeave();
    } else {
      setShowFinishModal(true);
    }
  };

  // "Confirm all and finish": mark every current candidate confirmed, flag the
  // step done, then leave. Sends the client's full candidate view so the server
  // can reject a stale set; only navigates once both writes land.
  const finishAndConfirmAll = () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    const candidateGroupIds = graphs.map((g) => g.candidate_group_id);
    beginRequest();
    api
      .post(`/api/projects/${projectIdNum}/parallel-blocks/confirmations/all`, {
        candidate_group_ids: candidateGroupIds,
      })
      .then(() => api.post(`/api/projects/${projectIdNum}/parallel-blocks/finish`, {}))
      .then(() => {
        setConfirmedSubjectIds(new Set(graphs.map((g) => g.subject.id)));
        // Drop the cached candidates payload so its confirmed flags are refetched.
        void queryClient.invalidateQueries({
          queryKey: queryKeys.projects.parallelCandidates(String(projectIdNum)),
        });
        // Refresh the project list so ProjectCard sees the updated flag.
        void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        setShowFinishModal(false);
        rememberView();
        void navigate(backRoute);
      })
      .catch((err: unknown) => {
        const code =
          err instanceof Error && "code" in err ? (err as ApiRequestError).code : undefined;
        if (code === ApiError.PARALLEL_CONFIRMATION_STALE) {
          // Candidates changed under us: refetch and prompt a re-check instead
          // of leaving with an incomplete confirmation.
          void queryClient.invalidateQueries({
            queryKey: queryKeys.projects.parallelCandidates(String(projectIdNum)),
          });
          setShowFinishModal(false);
          setStaleConfirmScope("all");
        } else {
          setSaveStatus({
            type: "error",
            message: err instanceof Error ? err.message : "Erro ao confirmar",
          });
        }
      })
      .finally(endRequest);
  };

  // Finish without confirming the rest: still marks the step done, so the user
  // won't be sent back here. Keeps the groups and confirmations already made.
  const finishContinue = () => {
    markSelectedAndLeave();
  };

  // Continue later: leave for the schedule (like the Horário button) without
  // marking the step done, so the home card routes back here next time.
  const finishLater = () => {
    setShowFinishModal(false);
    rememberView();
    void navigate(backRoute);
  };

  const handleReset = () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    setShowResetModal(true);
  };

  const confirmReset = () => {
    if (!projectId || Number.isNaN(projectIdNum)) return;
    rememberView();
    // Recomeçar clears the confirmed groups, every subject confirmation, and the
    // "selection done" flag, so the project starts the step over from scratch.
    Promise.all([
      api.delete(`/api/projects/${projectIdNum}/parallel-blocks/groups/`),
      api.delete(`/api/projects/${projectIdNum}/parallel-blocks/confirmations/`),
      api.delete(`/api/projects/${projectIdNum}/parallel-blocks/finish`),
    ])
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
    saving,
    saveStatus,
    showResetModal,
    setShowResetModal,
    confirmedSubjectIds,
    confirmedYearIds,
    confirmedDegreeIds,
    confirmSubject,
    unconfirmSubject,
    allYearsConfirmed,
    unconfirmedByDegree,
    showFinishModal,
    setShowFinishModal,
    staleConfirmScope,
    setStaleConfirmScope,
    handleFinish,
    finishAndConfirmAll,
    finishContinue,
    finishLater,
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
