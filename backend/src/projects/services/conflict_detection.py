"""Conflict detection across schedule sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from itertools import combinations

from src.projects.projects_db.models.session import Session

_WEEKDAY_LABELS: dict[str, str] = {
    "monday": "Seg",
    "tuesday": "Ter",
    "wednesday": "Qua",
    "thursday": "Qui",
    "friday": "Sex",
    "saturday": "Sáb",
    "sunday": "Dom",
}


@dataclass
class ConflictResult:
    id: str
    event_ids: list[str]
    event_names: list[str]
    day: str
    time: str
    turma: str
    conflict_reasons: list[str]


def _hhmm_to_minutes(hhmm: int) -> int:
    return (hhmm // 100) * 60 + (hhmm % 100)


def _format_time(hhmm: int) -> str:
    return f"{hhmm // 100:02d}:{hhmm % 100:02d}"


def _overlaps(a: Session, b: Session) -> bool:
    a_start = _hhmm_to_minutes(a.start_time)
    a_end = a_start + a.duration * 30
    b_start = _hhmm_to_minutes(b.start_time)
    b_end = b_start + b.duration * 30
    return a_start < b_end and b_start < a_end


def _session_name(session: Session) -> str:
    scs = session.session_class_subjects
    if scs:
        subject = scs[0].subject
        if subject is not None:
            return f"{subject.acronym} ({session.type})"
    return f"({session.type})"


def _conflict_id(a: Session, b: Session) -> str:
    # deterministic: sort the two UUIDs so order doesn't matter
    key = ",".join(sorted([str(a.id), str(b.id)]))
    return str(uuid.uuid5(uuid.NAMESPACE_OID, key))


def detect_conflicts(sessions: list[Session]) -> list[ConflictResult]:
    """Return one ConflictResult per pair of overlapping sessions that share a resource.

    Sessions must have teachers, rooms, and session_class_subjects (with subject
    and class_ sub-relationships) eagerly loaded before being passed here.
    """
    # Group by (week, weekday) to limit pairwise comparisons
    by_slot: dict[tuple, list[Session]] = {}
    for s in sessions:
        key = (s.week, s.weekday)
        by_slot.setdefault(key, []).append(s)

    results: list[ConflictResult] = []

    for slot_sessions in by_slot.values():
        for a, b in combinations(slot_sessions, 2):
            if not _overlaps(a, b):
                continue

            reasons: list[str] = []

            shared_teachers = {t.id for t in a.teachers} & {t.id for t in b.teachers}
            for teacher_id in shared_teachers:
                teacher = next(t for t in a.teachers if t.id == teacher_id)
                reasons.append(f"Prof. {teacher.name} em dois locais ao mesmo tempo")

            shared_rooms = {r.id for r in a.rooms} & {r.id for r in b.rooms}
            for room_id in shared_rooms:
                room = next(r for r in a.rooms if r.id == room_id)
                reasons.append(f"Sala {room.name} com dois eventos em simultâneo")

            a_class_ids = {scs.class_id for scs in a.session_class_subjects}
            b_class_ids = {scs.class_id for scs in b.session_class_subjects}
            shared_class_ids = a_class_ids & b_class_ids
            for class_id in shared_class_ids:
                scs = next(s for s in a.session_class_subjects if s.class_id == class_id)
                if scs.class_ is not None:
                    reasons.append(f"Turma {scs.class_.code} em duas sessões ao mesmo tempo")

            if not reasons:
                continue

            all_class_codes = sorted(
                {
                    scs.class_.code
                    for scs in (*a.session_class_subjects, *b.session_class_subjects)
                    if scs.class_ is not None
                },
            )

            results.append(
                ConflictResult(
                    id=_conflict_id(a, b),
                    event_ids=[str(a.id), str(b.id)],
                    event_names=[_session_name(a), _session_name(b)],
                    day=_WEEKDAY_LABELS.get(a.weekday.value, a.weekday.value),
                    time=_format_time(a.start_time),
                    turma=", ".join(all_class_codes),
                    conflict_reasons=reasons,
                ),
            )

    return results
