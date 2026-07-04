import { ApiError, type ApiErrorCode, type ApiRequestError } from "@/types/api";

/** The API error code carried on a rejected request, if any. */
export function getErrorCode(err: unknown): ApiErrorCode | undefined {
  return err instanceof Error && "code" in err ? (err as ApiRequestError).code : undefined;
}

/** The API error's human-readable message, or the given fallback. The raw
 * `Error.message` (e.g. "HTTP 500") is never surfaced to users. */
export function getErrorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? ((err as ApiRequestError).apiMessage ?? fallback) : fallback;
}

/** Message for a failed group create/delete: maps the invalid-candidates code
 * to a PT explanation, else falls back to the raw error message. */
export function parallelSaveErrorMessage(err: unknown): string {
  if (getErrorCode(err) === ApiError.PARALLEL_GROUPS_INVALID_CANDIDATES) {
    return "As turmas selecionadas não são candidatas a paralelas.";
  }
  return getErrorMessage(err, "Erro ao guardar");
}
