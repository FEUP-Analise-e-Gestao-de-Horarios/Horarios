import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/api/client";
import {
  type DegreeOption,
  type ParallelCandidateGraph,
  type UnconfirmedDegree,
  type UnconfirmedYear,
  type UUID,
} from "@/types/parallelSessions";
import { getErrorMessage } from "@/api/errors";
import { handleStaleConfirmError, type StaleConfirmScope } from "./errors";
import type { SavingControls } from "./saving";

/** Owns the "reviewed" state of subjects and the confirmation roll-up
 * (subject → year → degree) computed across the whole payload, plus the
 * optimistic confirm/unconfirm writes and the stale-confirm prompt scope. */
export function useParallelConfirmations(params: {
  projectIdNum: number;
  projectValid: boolean;
  candidatesData: ParallelCandidateGraph[] | undefined;
  loadingCandidates: boolean;
  graphs: ParallelCandidateGraph[];
  saving: SavingControls;
}) {
  const { projectIdNum, projectValid, candidatesData, loadingCandidates, graphs } = params;
  const { beginRequest, endRequest } = params.saving;
  const queryClient = useQueryClient();

  // Subjects the user has marked reviewed. Seeded from the payload (a subject is
  // confirmed when all its candidates are) and then mutated optimistically.
  const [confirmedSubjectIds, setConfirmedSubjectIds] = useState<Set<UUID>>(new Set());
  // Set when a confirm is rejected because the candidates changed under the
  // user; the list is refetched and this prompts a re-check. The scope drives
  // the prompt copy: a single subject vs. the finish-all action.
  const [staleConfirmScope, setStaleConfirmScope] = useState<StaleConfirmScope>(null);

  // Server truth: the subject ids the payload currently reports as confirmed. A
  // subject is confirmed when every one of its candidates is (carried on
  // `subject.confirmed`).
  const serverConfirmedSubjectIds = useMemo(() => {
    const set = new Set<UUID>();
    if (!candidatesData) return set;
    for (const g of candidatesData) {
      if (g.subject.confirmed) set.add(g.subject.id);
    }
    return set;
  }, [candidatesData]);

  // -- Seed confirmed subjects from the loaded candidate payload --------
  // Re-derives the local set whenever the *content* of the server-confirmed set
  // changes (keyed per project). Keying on content — not on the query's identity
  // — means an unrelated refetch can't clobber an in-flight optimistic confirm/
  // unconfirm (the server flags are unchanged, so the signature matches and we
  // skip), while a stale-confirm invalidation, which does change those flags,
  // re-applies server truth as intended.
  const seededSignatureRef = useRef<string | null>(null);
  useEffect(() => {
    if (loadingCandidates || !candidatesData) return;
    const signature = `${projectIdNum}:${[...serverConfirmedSubjectIds].sort().join(",")}`;
    if (seededSignatureRef.current === signature) return;
    seededSignatureRef.current = signature;
    setConfirmedSubjectIds(new Set(serverConfirmedSubjectIds));
  }, [candidatesData, loadingCandidates, projectIdNum, serverConfirmedSubjectIds]);

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

  // -- Confirmation persistence -----------------------------------------
  // Confirm/unconfirm a whole subject: the server resolves the subject's
  // current candidate ids and stores/removes them. Optimistic, rolling back on
  // failure. A pure "reviewed" flag — independent of whether groups were made.
  // Resolves true when the confirm landed, false when it was rejected (rolled
  // back) — so the caller can undo any optimistic UI (e.g. the auto-jump).
  const confirmSubject = (subjectId: UUID): Promise<boolean> => {
    if (!projectValid) return Promise.resolve(false);
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
        handleStaleConfirmError(err, {
          queryClient,
          projectIdNum,
          setStaleConfirmScope,
          scope: "subject",
        });
        return false;
      })
      .finally(endRequest);
  };

  const unconfirmSubject = (subjectId: UUID) => {
    if (!projectValid) return;
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
        toast.error(getErrorMessage(err, "Erro ao repor"));
      })
      .finally(endRequest);
  };

  return {
    confirmedSubjectIds,
    setConfirmedSubjectIds,
    confirmedYearIds,
    confirmedDegreeIds,
    unconfirmedByDegree,
    allYearsConfirmed,
    confirmSubject,
    unconfirmSubject,
    staleConfirmScope,
    setStaleConfirmScope,
  };
}
