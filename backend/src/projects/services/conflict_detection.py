"""Conflict detection across schedule sessions."""

from __future__ import annotations

import uuid
from itertools import combinations

from src.projects.projects_db.models.session import Session
from src.projects.services.schemas.conflicts import ConflictResult


def _hhmm_to_minutes(hhmm: int) -> int:
    return (hhmm // 100) * 60 + (hhmm % 100)


def _overlaps(session_a: Session, session_b: Session) -> bool:
    start_a = _hhmm_to_minutes(session_a.start_time)
    end_a = start_a + session_a.duration * 30
    start_b = _hhmm_to_minutes(session_b.start_time)
    end_b = start_b + session_b.duration * 30
    return start_a < end_b and start_b < end_a


def _session_name(session: Session) -> str:
    class_subjects = session.session_class_subjects
    if class_subjects:
        subject = class_subjects[0].subject
        if subject is not None:
            return f"{subject.acronym} ({session.type})"
    return f"({session.type})"


def _conflict_id(session_a: Session, session_b: Session) -> str:
    # deterministic: sort the two UUIDs so order doesn't matter
    key = ",".join(sorted([str(session_a.id), str(session_b.id)]))
    return str(uuid.uuid5(uuid.NAMESPACE_OID, key))


def detect_conflicts(sessions: list[Session]) -> list[ConflictResult]:
    """Return one ConflictResult per pair of overlapping sessions that share a resource.

    Sessions must have teachers, rooms, and session_class_subjects (with subject
    and class_ sub-relationships) eagerly loaded before being passed here.
    """
    # Group by (week, weekday) to limit pairwise comparisons
    by_slot: dict[tuple, list[Session]] = {}
    for session in sessions:
        key = (session.week, session.weekday)
        by_slot.setdefault(key, []).append(session)

    results: list[ConflictResult] = []

    for slot_sessions in by_slot.values():
        for session_a, session_b in combinations(slot_sessions, 2):
            if not _overlaps(session_a, session_b):
                continue

            reasons: list[str] = []

            shared_teachers = {teacher.id for teacher in session_a.teachers} & {
                teacher.id for teacher in session_b.teachers
            }
            for teacher_id in shared_teachers:
                teacher = next(
                    teacher for teacher in session_a.teachers if teacher.id == teacher_id
                )
                reasons.append(f"Prof. {teacher.name} em dois locais ao mesmo tempo")

            shared_rooms = {room.id for room in session_a.rooms} & {
                room.id for room in session_b.rooms
            }
            for room_id in shared_rooms:
                room = next(room for room in session_a.rooms if room.id == room_id)
                reasons.append(f"Sala {room.name} com dois eventos em simultâneo")

            session_a_class_ids = {
                class_subject.class_id for class_subject in session_a.session_class_subjects
            }
            session_b_class_ids = {
                class_subject.class_id for class_subject in session_b.session_class_subjects
            }
            shared_class_ids = session_a_class_ids & session_b_class_ids
            for class_id in shared_class_ids:
                class_subject = next(
                    cs for cs in session_a.session_class_subjects if cs.class_id == class_id
                )
                if class_subject.class_ is not None:
                    reasons.append(
                        f"Turma {class_subject.class_.code} em duas sessões ao mesmo tempo",
                    )

            if not reasons:
                continue

            all_class_codes = sorted(
                {
                    class_subject.class_.code
                    for class_subject in (
                        *session_a.session_class_subjects,
                        *session_b.session_class_subjects,
                    )
                    if class_subject.class_ is not None
                },
            )

            results.append(
                ConflictResult(
                    id=_conflict_id(session_a, session_b),
                    event_ids=[str(session_a.id), str(session_b.id)],
                    event_names=[_session_name(session_a), _session_name(session_b)],
                    day=session_a.weekday.value,
                    time=session_a.start_time,
                    turma=all_class_codes,
                    conflict_reasons=reasons,
                ),
            )

    return results
