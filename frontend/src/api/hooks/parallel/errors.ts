import { getErrorCode, getErrorMessage } from "@/api/errors";
import { ApiError } from "@/types/api";

/** Message for a failed group create/delete: maps the invalid-candidates code
 * to a PT explanation, else falls back to the raw error message. */
export function parallelSaveErrorMessage(err: unknown): string {
  if (getErrorCode(err) === ApiError.PARALLEL_GROUPS_INVALID_CANDIDATES) {
    return "As turmas selecionadas não são candidatas a paralelas.";
  }
  return getErrorMessage(err, "Erro ao guardar");
}
