import { redirect } from "react-router-dom";
import type { User } from "../types/user";
import { ROUTES } from "../routes";

export async function requireAuth(): Promise<User | Response> {
  const res = await fetch("/api/auth/me", { credentials: "same-origin" });
  if (!res.ok) return redirect(ROUTES.LOGIN);
  return (await res.json()) as User;
}

// Used on public auth pages (login, forgot-password). Hitting /api/auth/me
// primes the CSRF cookie so subsequent POSTs pass the CSRF check — this
// matters in dev, where Vite serves index.html directly and Django's
// spa_view (which also ensures the cookie) never runs.
export async function redirectIfAuthenticated(): Promise<Response | null> {
  const res = await fetch("/api/auth/me", { credentials: "same-origin" });
  if (res.ok) return redirect(ROUTES.HOME);
  return null;
}
