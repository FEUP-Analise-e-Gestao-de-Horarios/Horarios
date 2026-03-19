import { redirect } from "react-router-dom";
import type { User } from "../types/user";
import { ROUTES } from "../routes";

export async function requireAuth(): Promise<User | Response> {
  const res = await fetch("/api/auth/me", { credentials: "same-origin" });
  if (!res.ok) return redirect(ROUTES.LOGIN);
  return (await res.json()) as User;
}
