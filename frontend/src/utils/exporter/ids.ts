export function normalizeId(value: string): string {
  return value.replaceAll("-", "");
}

export function anchorId(sessionId: string): string {
  return `change-${normalizeId(sessionId)}`;
}

export function anchorPart(value: string | number | undefined): string {
  return String(value ?? "unknown").replace(/[^a-zA-Z0-9_-]/g, "-");
}

export function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…` : value;
}
