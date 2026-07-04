import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import {
  DAY_ORDER,
  type ParallelBlockNode,
  type ParallelCandidateGraph,
  type ParallelGroup,
  type SuccessResponse,
  type UUID,
} from "@/types/parallelSessions";
import { parallelSaveErrorMessage } from "./errors";
import type { SavingControls } from "./useSaving";

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

/** A confirmed/draft group enriched with display metadata for the side panel. */
export interface GroupView {
  group: ParallelGroup;
  subjectName: string;
  weekday: string;
  startTime: number;
  blocks: { blockId: UUID; type: string; codes: string[] }[];
}

/** Owns the local group list and its optimistic create/delete lifecycle: a
 * `createGroup` primitive (selection-agnostic), `handleRemoveGroup`, plus the
 * derived `assignedBlockIds` and per-subject group views for the side panel. */
export function useParallelGroups(params: {
  projectIdNum: number;
  candidatesData: ParallelCandidateGraph[] | undefined;
  loadingCandidates: boolean;
  graphs: ParallelCandidateGraph[];
  selectedYearIds: Set<UUID>;
  saving: SavingControls;
}) {
  const { projectIdNum, candidatesData, loadingCandidates, graphs, selectedYearIds } = params;
  const { beginRequest, endRequest } = params.saving;
  const queryClient = useQueryClient();

  const [groups, setGroups] = useState<ParallelGroup[]>([]);

  // In-flight create requests, keyed by local group id, resolving to the
  // backend group id (or null on failure). A delete can await one so it can
  // remove a group whose create round-trip has not landed yet.
  const pendingCreates = useRef<Map<string, Promise<UUID | null>>>(new Map());

  // -- Seed confirmed groups from the loaded candidate payload ----------
  // Server truth: the confirmed groups the payload currently reports, each with
  // its block membership. Every node carries the confirmed_group_id it is saved
  // under, so confirmed groups are fully derivable from the payload; drafts live
  // only in local state.
  const serverConfirmedGroups = useMemo(() => {
    const byConfirmed = new Map<string, ParallelGroup>();
    if (!candidatesData) return byConfirmed;
    for (const g of candidatesData) {
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
    return byConfirmed;
  }, [candidatesData]);

  // Re-derives the seeded confirmed groups whenever the *content* of the
  // server-confirmed set changes (block membership included), keyed per project.
  // Keying on content — not the query's identity — means an unrelated refetch
  // can't clobber an in-flight optimistic create/delete: the server groups are
  // unchanged, so the signature matches and we skip. A stale-confirm
  // invalidation, which does change block membership, re-applies server truth so
  // cards stop resolving against dropped ids. The re-seed reconciles by server
  // id so existing cards keep their React identity (no remount / interrupted
  // animation); optimistic pending cards (still creating, or on their way out)
  // are carried across untouched.
  const seededSignatureRef = useRef<string | null>(null);
  useEffect(() => {
    if (loadingCandidates || !candidatesData) return;
    const signature = `${projectIdNum}:${[...serverConfirmedGroups.values()]
      .map((g) => `${g.serverId}:${[...g.blockIds].sort().join("-")}`)
      .sort()
      .join(",")}`;
    if (seededSignatureRef.current === signature) return;
    seededSignatureRef.current = signature;

    setGroups((prev) => {
      // Index existing cards that carry a server id, so a group already present
      // keeps its React identity (no remount / animation restart) across a
      // re-seed; only genuinely new server groups mount, and settled cards that
      // vanished server-side drop out.
      const prevByServerId = new Map<UUID, ParallelGroup>();
      for (const g of prev) if (g.serverId) prevByServerId.set(g.serverId, g);

      const next: ParallelGroup[] = [];
      const seeded = new Set<UUID>();
      for (const [sid, serverGrp] of serverConfirmedGroups) {
        seeded.add(sid);
        const existing = prevByServerId.get(sid);
        // Reuse the existing card (keep id + in-flight status), just refresh
        // block membership from server truth; mount a fresh card only for new
        // groups.
        next.push(existing ? { ...existing, blockIds: serverGrp.blockIds } : serverGrp);
      }
      // Carry optimistic cards the server doesn't (yet) know about: pending
      // creates with no serverId, and deleting/leaving cards whose group is
      // already gone. A "saved" card missing from server truth is dropped.
      for (const g of prev) {
        if (g.serverId && seeded.has(g.serverId)) continue;
        if (g.status !== "saved") next.push(g);
      }
      return next;
    });
  }, [candidatesData, loadingCandidates, projectIdNum, serverConfirmedGroups]);

  // -- Lookups ----------------------------------------------------------
  const nodeIndex = useMemo(() => {
    const map = new Map<UUID, { node: ParallelBlockNode; graph: ParallelCandidateGraph }>();
    for (const g of graphs) {
      for (const node of g.nodes) map.set(node.original_block_id, { node, graph: g });
    }
    return map;
  }, [graphs]);

  const assignedBlockIds = useMemo(() => new Set(groups.flatMap((g) => g.blockIds)), [groups]);

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
        selectedYearIds.size > 0 &&
        !blocks.some((e) => e.node.classes.some((c) => selectedYearIds.has(c.year_id)))
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
  }, [groups, nodeIndex, selectedYearIds]);

  // -- Per-action persistence -------------------------------------------
  // Every create/remove hits the backend immediately with an optimistic UI
  // update that rolls back if the request fails.

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
        toast.error(parallelSaveErrorMessage(err));
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
  const persistDelete = async (
    group: ParallelGroup,
    { invalidate = true }: { invalidate?: boolean } = {},
  ): Promise<void> => {
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
      // Suppressed for the bulk path, which invalidates once after all its
      // deletes land instead of per card.
      if (invalidate) void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });

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
      toast.error(parallelSaveErrorMessage(err));
    } finally {
      endRequest();
    }
  };

  // Selection-agnostic create primitive: optimistically add a "creating" card
  // for the given blocks and kick off its persistence. Returns the local id.
  const createGroup = (candidateGroupId: UUID, blockIds: UUID[]): UUID => {
    const id = crypto.randomUUID();
    setGroups((prev) => [
      ...prev,
      { id, serverId: null, candidateGroupId, blockIds, status: "creating" },
    ]);
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

  // Bulk remove (Repor): flag every eligible card for deletion, fire all the
  // deletes concurrently with their per-card invalidation suppressed, then
  // invalidate the project cache exactly once after they all settle — collapsing
  // N candidates refetches into one. Per-card animation timing is untouched.
  const handleRemoveGroups = (groupIds: string[]) => {
    const targets = groupIds
      .map((id) => groups.find((g) => g.id === id))
      .filter(
        (g): g is ParallelGroup => g != null && g.status !== "deleting" && g.status !== "leaving",
      );
    if (targets.length === 0) return;
    const targetIds = new Set(targets.map((g) => g.id));
    setGroups((prev) => prev.map((g) => (targetIds.has(g.id) ? { ...g, status: "deleting" } : g)));
    // allSettled so one failed delete still lets the single invalidation run.
    void Promise.allSettled(
      targets.map((group) => persistDelete(group, { invalidate: false })),
    ).then(() => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
    });
  };

  return {
    assignedBlockIds,
    groupViewsBySubject,
    createGroup,
    handleRemoveGroup,
    handleRemoveGroups,
  };
}
