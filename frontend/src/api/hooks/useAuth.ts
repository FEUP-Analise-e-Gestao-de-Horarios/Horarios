import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import { ApiError } from "@/types/api";
import type { ApiRequestError } from "@/types/api";

export function useLogin() {
  return useMutation<
    void,
    ApiRequestError<typeof ApiError.INVALID_JSON | typeof ApiError.AUTH_BAD_CREDENTIALS>,
    { username: string; password: string }
  >({
    mutationFn: (data) => api.post<void>("/api/auth/login", data),
  });
}

export function useLogout() {
  return useMutation<void, ApiRequestError<never>, void>({
    mutationFn: () => api.post<void>("/api/auth/logout", {}),
  });
}

export function useChangePassword() {
  return useMutation<
    void,
    ApiRequestError<
      | typeof ApiError.AUTH_NOT_AUTHENTICATED
      | typeof ApiError.INVALID_JSON
      | typeof ApiError.AUTH_INVALID_OLD_PASSWORD
      | typeof ApiError.AUTH_PASSWORD_POLICY_VIOLATION
    >,
    { old_password: string; new_password: string }
  >({
    mutationFn: (data) => api.post<void>("/api/auth/change_password", data),
  });
}

export function useForgotPassword() {
  return useMutation<
    void,
    ApiRequestError<typeof ApiError.AUTH_ALREADY_AUTHENTICATED | typeof ApiError.INVALID_JSON>,
    { email: string }
  >({
    mutationFn: (data) => api.post<void>("/api/auth/forgot-password", data),
  });
}
