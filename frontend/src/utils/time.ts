/**
 * Converts an `HHMM`-encoded integer (e.g. 1430 for 14:30) into minutes since
 * midnight.
 */
export function hhmmToMinutes(hhmm: number): number {
  const hours = Math.floor(hhmm / 100);
  const minutes = hhmm % 100;
  return hours * 60 + minutes;
}

/** Formats minutes since midnight as a zero-padded `HH:MM` string. */
export function minutesToTime(totalMinutes: number): string {
  const hours = String(Math.floor(totalMinutes / 60)).padStart(2, "0");
  const minutes = String(totalMinutes % 60).padStart(2, "0");
  return `${hours}:${minutes}`;
}

/** Formats a count of 30-min slots as a duration label: "30min", "1h", "1h30". */
export function formatDurationSlots(slots: number): string {
  const totalMinutes = slots * 30;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `${minutes}min`;
  if (minutes === 0) return `${hours}h`;
  return `${hours}h${String(minutes).padStart(2, "0")}`;
}
