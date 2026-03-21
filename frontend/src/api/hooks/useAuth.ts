import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ApiRequestError } from "@/types/api";

export function useLogin() {
  return useMutation<void, ApiRequestError, { username: string; password: string }>({
    mutationFn: (data) => api.post<void>("/api/auth/login", data),
  });
}

export function useLogout() {
  return useMutation<void, ApiRequestError, void>({
    mutationFn: () => api.post<void>("/api/auth/logout", {}),
  });
}

export function useChangePassword() {
  return useMutation<void, ApiRequestError, { old_password: string; new_password: string }>({
    mutationFn: (data) => api.post<void>("/api/auth/change_password", data),
  });
}

export function useForgotPassword() {
  return useMutation<void, ApiRequestError, { email: string }>({
    mutationFn: (data) => api.post<void>("/api/auth/forgot-password", data),
  });
}
