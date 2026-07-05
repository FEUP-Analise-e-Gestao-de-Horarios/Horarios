import type { Dispatch, SetStateAction } from "react";
import type { QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getErrorCode, getErrorMessage } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { ApiError } from "@/types/api";

/** Message for a failed group create/delete: maps the invalid-candidates code
 * to a PT explanation, else falls back to the raw error message. */
export function parallelSaveErrorMessage(err: unknown): string {
  if (getErrorCode(err) === ApiError.PARALLEL_GROUPS_INVALID_CANDIDATES) {
    return "As turmas selecionadas não são candidatas a paralelas.";
  }
  return getErrorMessage(err, "Erro ao guardar");
}

/** Re-check scope prompted after a stale confirmation, or null when clear. */
export type StaleConfirmScope = "subject" | "all" | null;

/** Handle a confirm/finish write failure. On a stale candidate set, refetch the
 * candidates and flag the given re-check scope (running `onStale` first for any
 * extra cleanup, e.g. closing the finish modal); otherwise toast a fallback. */
export function handleStaleConfirmError(
  err: unknown,
  opts: {
    queryClient: QueryClient;
    projectIdNum: number;
    setStaleConfirmScope: Dispatch<SetStateAction<StaleConfirmScope>>;
    scope: Exclude<StaleConfirmScope, null>;
    onStale?: () => void;
  },
): void {
  if (getErrorCode(err) === ApiError.PARALLEL_CONFIRMATION_STALE) {
    void opts.queryClient.invalidateQueries({
      queryKey: queryKeys.projects.parallelCandidates(String(opts.projectIdNum)),
    });
    opts.onStale?.();
    opts.setStaleConfirmScope(opts.scope);
  } else {
    toast.error(getErrorMessage(err, "Erro ao confirmar"));
  }
}
