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

  // Generic
  INVALID_JSON: "generic.invalid_json",
  INVALID_BODY: "generic.invalid_body",
} as const;

export type ApiErrorCode = (typeof ApiError)[keyof typeof ApiError];

export interface ApiRequestError extends Error {
  code?: ApiErrorCode;
  apiMessage?: string;
  status?: number;
}
