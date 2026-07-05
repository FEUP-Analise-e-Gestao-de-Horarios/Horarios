export const ApiError = {
  // Projects
  PROJECTS_CREATE_DUPLICATED_NAME: "projects.create.duplicated_name",
  PROJECTS_CREATE_FAILED: "projects.create.failed",
  PROJECTS_NOT_FOUND: "projects.not_found",
  PROJECTS_RENAME_DUPLICATED_NAME: "projects.rename.duplicated_name",

  // Auth
  AUTH_NOT_AUTHENTICATED: "auth.not_authenticated",
  AUTH_ALREADY_AUTHENTICATED: "auth.already_authenticated",
  AUTH_BAD_CREDENTIALS: "auth.bad_credentials",
  AUTH_INVALID_OLD_PASSWORD: "auth.invalid_old_password",
  AUTH_PASSWORD_POLICY_VIOLATION: "auth.password_policy_violation",

  // Parallel groups
  PARALLEL_GROUPS_INVALID_CANDIDATES: "projects.parallel_groups.invalid_candidates",
  PARALLEL_GROUPS_NOT_FOUND: "projects.parallel_groups.not_found",
  PARALLEL_CONFIRMATION_STALE: "projects.parallel_confirmation.stale",

  // Generic
  INVALID_JSON: "generic.invalid_json",
  INVALID_BODY: "generic.invalid_body",
} as const;

export type ApiErrorCode = (typeof ApiError)[keyof typeof ApiError];

export interface ApiRequestError<T extends ApiErrorCode = ApiErrorCode> extends Error {
  code?: T;
  apiMessage?: string;
  status?: number;
}

export interface ApiResponse<T> {
  data: T;
}
