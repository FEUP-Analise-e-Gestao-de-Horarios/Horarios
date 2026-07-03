export function exporterScrollStorageKey(projectId: string): string {
  return `exporter-scroll-top:${projectId}`;
}

export function exporterSelectedConflictStorageKey(projectId: string): string {
  return `exporter-selected-conflict:${projectId}`;
}

export function exporterConflictsOpenStorageKey(projectId: string): string {
  return `exporter-conflicts-open:${projectId}`;
}

export function parseStoredScrollTop(savedScrollTop: string | null): number | null {
  if (savedScrollTop === null) return null;

  const parsedScrollTop = Number(savedScrollTop);
  if (Number.isNaN(parsedScrollTop)) return null;

  return parsedScrollTop;
}

export function shouldRestoreExporterScroll(args: {
  projectId: string;
  restoredProjectId: string | null;
  hasSelectedConflict: boolean;
  savedScrollTop: number | null;
}): boolean {
  const { projectId, restoredProjectId, hasSelectedConflict, savedScrollTop } = args;
  if (!projectId) return false;
  if (restoredProjectId === projectId) return false;
  if (hasSelectedConflict) return false;
  return savedScrollTop !== null;
}
