import { redirect } from "react-router-dom";
import type { User } from "../types/user";

export async function requireAuth(): Promise<User | Response> {
  const res = await fetch("/api/auth/me", { credentials: "same-origin" });
  if (!res.ok) return redirect("/login");
  return (await res.json()) as User;
}
