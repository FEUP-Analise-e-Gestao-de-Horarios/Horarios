"""Conflict detection across schedule sessions."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.conflict_dao import ConflictDAO
from src.projects.projects_db.models.session import Session
from src.projects.services.schemas.conflicts import ConflictData, ConflictResult


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


def _group_conflict_id(block_ids: list[UUID]) -> str:
    """Deterministic conflict ID based on sorted block IDs of the conflicting group."""
    key = ",".join(sorted(str(bid) for bid in block_ids))
    return str(uuid.uuid5(uuid.NAMESPACE_OID, key))


def _find_conflict_groups(
    sessions: list[Session],
    block_weeks: dict[UUID, set],
) -> list[list[Session]]:
    """Group sessions into connected components of the overlap graph.

    Two sessions are connected if they overlap in time AND their blocks share
    at least one common week (blocks that never co-occur cannot conflict).
    Transitively connected sessions form one group, so N sessions all booked
    at the same time produce a single group rather than C(N,2) pairs.
    """
    n = len(sessions)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            weeks_i = block_weeks.get(sessions[i].original_block_id, set())
            weeks_j = block_weeks.get(sessions[j].original_block_id, set())
            if _overlaps(sessions[i], sessions[j]) and weeks_i & weeks_j:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj

    components: dict[int, list[Session]] = defaultdict(list)
    for i, s in enumerate(sessions):
        components[find(i)].append(s)

    return [comp for comp in components.values() if len(comp) >= 2]


# ---------------------------------------------------------------------------
# Grouped conflict computation (used for persistence and preview)
# ---------------------------------------------------------------------------


def _dedup_by_block(sessions: list[Session]) -> list[Session]:
    """Return one representative session per original_block_id."""
    seen: set[UUID] = set()
    result: list[Session] = []
    for s in sessions:
        if s.original_block_id not in seen:
            seen.add(s.original_block_id)
            result.append(s)
    return result


def _compute_conflict_rows(sessions: list[Session]) -> ConflictData:
    """Compute rows for the 6 normalized conflict tables.

    Returns a ConflictData with one entry per unique conflict_id in
    conflict_rows, plus junction rows for sessions, teachers, rooms, and
    classes. Sessions must have teachers, rooms, and session_class_subjects
    (with subject and class_ sub-relationships) eagerly loaded.

    The conflict_id is derived from the sorted block IDs of the group so all
    resource types that involve the same sessions share the same conflict_id.
    """
    data = ConflictData()
    seen_conflict_ids: set[UUID] = set()
    seen_session_pairs: set[tuple[UUID, UUID]] = set()
    seen_resource_pairs: set[tuple[UUID, UUID]] = set()

    block_weeks: dict[UUID, set] = defaultdict(set)
    for s in sessions:
        block_weeks[s.original_block_id].add(s.week)

    def _emit_group(group: list[Session], resource_id: UUID, resource_type: str) -> None:
        conflict_id = UUID(_group_conflict_id([s.original_block_id for s in group]))
        if conflict_id not in seen_conflict_ids:
            seen_conflict_ids.add(conflict_id)
            data.conflict_rows.append({"conflict_id": conflict_id})
        for session in group:
            key = (conflict_id, session.id)
            if key not in seen_session_pairs:
                seen_session_pairs.add(key)
                data.session_rows.append({"conflict_id": conflict_id, "session_id": session.id})
        resource_key = (conflict_id, resource_id)
        if resource_key not in seen_resource_pairs:
            seen_resource_pairs.add(resource_key)
            if resource_type == "teacher_id":
                data.teacher_rows.append({"conflict_id": conflict_id, resource_type: resource_id})
            elif resource_type == "room_id":
                data.room_rows.append({"conflict_id": conflict_id, resource_type: resource_id})
            elif resource_type == "class_id":
                data.class_rows.append({"conflict_id": conflict_id, resource_type: resource_id})

    def _emit_resource_groups(
        by_resource: dict[UUID, list[Session]],
        resource_type: str,
        *,
        guard: Callable[[list[Session], UUID], bool] | None = None,
    ) -> None:
        """For each resource, dedup sessions by block, group by weekday, find conflict
        groups, and call _emit_group — with an optional per-group guard predicate."""
        for resource_id, rsessions in by_resource.items():
            deduped = _dedup_by_block(rsessions)
            by_weekday: dict[object, list[Session]] = {}
            for s in deduped:
                by_weekday.setdefault(s.weekday, []).append(s)
            for weekday_sessions in by_weekday.values():
                for group in _find_conflict_groups(weekday_sessions, block_weeks):
                    if guard is not None and not guard(group, resource_id):
                        continue
                    _emit_group(group, resource_id, resource_type)

    # --- Teacher conflicts ---
    by_teacher: dict[UUID, list[Session]] = {}
    for session in sessions:
        for teacher in session.teachers:
            by_teacher.setdefault(teacher.id, []).append(session)
    _emit_resource_groups(by_teacher, "teacher_id")

    # --- Room conflicts ---
    by_room: dict[UUID, list[Session]] = {}
    for session in sessions:
        for room in session.rooms:
            by_room.setdefault(room.id, []).append(session)
    _emit_resource_groups(by_room, "room_id")

    # --- Class conflicts ---
    by_class: dict[UUID, list[Session]] = {}
    for session in sessions:
        for cs in session.session_class_subjects:
            if cs.class_ is not None:
                by_class.setdefault(cs.class_id, []).append(session)

    def _different_subjects(group: list[Session], class_id: UUID) -> bool:
        return (
            len(
                {
                    scs.subject_id
                    for s in group
                    for scs in s.session_class_subjects
                    if scs.class_id == class_id
                },
            )
            > 1
        )

    _emit_resource_groups(by_class, "class_id", guard=_different_subjects)

    return data


def _conflict_data_to_results(
    data: ConflictData,
    all_sessions: list,
) -> list[ConflictResult]:
    """Convert a ConflictData into ConflictResult objects using in-memory session data."""
    session_map = {s.id: s for s in all_sessions}

    sessions_by_conflict: dict[str, list] = defaultdict(list)
    for row in data.session_rows:
        cid = str(row["conflict_id"])
        session = session_map.get(row["session_id"])
        if session is not None:
            sessions_by_conflict[cid].append(session)

    teacher_ids_by_conflict: dict[str, list[UUID]] = defaultdict(list)
    for row in data.teacher_rows:
        teacher_ids_by_conflict[str(row["conflict_id"])].append(row["teacher_id"])

    room_ids_by_conflict: dict[str, list[UUID]] = defaultdict(list)
    for row in data.room_rows:
        room_ids_by_conflict[str(row["conflict_id"])].append(row["room_id"])

    class_ids_by_conflict: dict[str, list[UUID]] = defaultdict(list)
    for row in data.class_rows:
        class_ids_by_conflict[str(row["conflict_id"])].append(row["class_id"])

    results: list[ConflictResult] = []
    for cid, sessions in sessions_by_conflict.items():
        if not sessions:
            continue
        first = sessions[0]

        teacher_map = {t.id: t for s in sessions for t in s.teachers}
        room_map = {r.id: r for s in sessions for r in s.rooms}
        class_map = {
            cs.class_id: cs.class_
            for s in sessions
            for cs in s.session_class_subjects
            if cs.class_ is not None
        }

        turma = sorted(
            {
                cs.class_.code
                for s in sessions
                for cs in s.session_class_subjects
                if cs.class_ is not None
            },
        )

        reasons: list[str] = []
        for teacher_id in teacher_ids_by_conflict.get(cid, []):
            teacher = teacher_map.get(teacher_id)
            if teacher:
                reasons.append(f"Prof. {teacher.name} em aulas diferentes ao mesmo tempo")
        for room_id in room_ids_by_conflict.get(cid, []):
            room = room_map.get(room_id)
            if room:
                reasons.append(f"Sala {room.name} com aulas diferentes ao mesmo tempo")
        for class_id in class_ids_by_conflict.get(cid, []):
            class_ = class_map.get(class_id)
            if class_:
                reasons.append(f"Turma {class_.code} em aulas diferentes ao mesmo tempo")

        results.append(
            ConflictResult(
                id=cid,
                event_ids=[str(s.id) for s in sessions],
                event_names=[_session_name(s) for s in sessions],
                day=first.weekday.value,
                time=first.start_time,
                turma=turma,
                conflict_reasons=reasons,
            ),
        )

    return results


def get_live_conflicts(db_session: DBSession, sessions: list[Session]) -> list[ConflictResult]:
    """Detect conflicts from live session data and overlay any stored tags.

    Sessions must have teachers, rooms, and session_class_subjects (with subject
    and class_ sub-relationships) eagerly loaded.
    """
    data = _compute_conflict_rows(sessions)
    results = _conflict_data_to_results(data, sessions)

    tag_assignments = ConflictDAO(db_session).get_tag_assignments()
    for result in results:
        if result.id in tag_assignments:
            result.tag = tag_assignments[result.id]

    return results
