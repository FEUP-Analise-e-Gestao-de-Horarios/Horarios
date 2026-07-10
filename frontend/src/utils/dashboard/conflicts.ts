import type { RedBlockBase } from "@/types/project/red_block";
import type { SessionResponse } from "@/types/project/sessions";

const SLOT_MINUTES = 30;

function hhmmToMinutes(hhmm: number): number {
  return Math.floor(hhmm / 100) * 60 + (hhmm % 100);
}

function overlaps(startA: number, endA: number, startB: number, endB: number): boolean {
  return startA < endB && startB < endA;
}

export function findConflictingSessionIds(
  sessions: SessionResponse[],
  redBlocks: RedBlockBase[] = [],
): Set<string> {
  const conflictingIds = new Set<string>();

  sessions.forEach((session, i) => {
    const start = hhmmToMinutes(session.start_time);
    const end = start + session.duration * SLOT_MINUTES;

    for (const candidate of sessions.slice(i + 1)) {
      if (candidate.weekday !== session.weekday) continue;
      const candidateStart = hhmmToMinutes(candidate.start_time);
      const candidateEnd = candidateStart + candidate.duration * SLOT_MINUTES;
      if (overlaps(start, end, candidateStart, candidateEnd)) {
        conflictingIds.add(session.id);
        conflictingIds.add(candidate.id);
      }
    }

    if (
      redBlocks.some((block) => {
        if (block.weekday !== session.weekday) return false;
        const blockStart = hhmmToMinutes(block.hour);
        return overlaps(start, end, blockStart, blockStart + SLOT_MINUTES);
      })
    ) {
      conflictingIds.add(session.id);
    }
  });

  return conflictingIds;
}

export function findConflictWeeks(
  blocks: { weeks: string[]; sessions: SessionResponse[] }[],
  redBlocks: RedBlockBase[] = [],
): Set<string> {
  return new Set(
    blocks.flatMap((block) =>
      findConflictingSessionIds(block.sessions, redBlocks).size > 0 ? block.weeks : [],
    ),
  );
}
