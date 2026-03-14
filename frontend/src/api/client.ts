function getCsrfToken(): string {
  return (
    document.cookie
      .split("; ")
      .find((row) => row.startsWith("csrftoken="))
      ?.split("=")[1] ?? ""
  );
}

async function request<T>(
  url: string,
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
  data?: unknown,
): Promise<T> {
  const res = await fetch(url, {
    method,
    credentials: "same-origin", // send session cookie
    headers: {
      "Content-Type": "application/json",
      ...(method !== "GET" && { "X-CSRFToken": getCsrfToken() }),
    },
    ...(data !== undefined ? { body: JSON.stringify(data) } : {}),
  });

  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(url: string) => request<T>(url, "GET"),
  post: <T>(url: string, data: unknown) => request<T>(url, "POST", data),
  put: <T>(url: string, data: unknown) => request<T>(url, "PUT", data),
  patch: <T>(url: string, data: unknown) => request<T>(url, "PATCH", data),
  delete: <T>(url: string) => request<T>(url, "DELETE"),
};
