"""Conflict detection across schedule sessions."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.conflict_dao import ConflictDAO
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.models.class_red_block import ClassRedBlock
from src.projects.projects_db.models.room_red_block import RoomRedBlock
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.teacher_red_block import TeacherRedBlock
from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.services.schemas.conflicts import ConflictData, ConflictResult, RedBlocks

# A red block marks a single 30-minute slot as unavailable.
RED_BLOCK_SLOT_MINUTES = 30


def load_conflict_sessions(db_session: DBSession) -> tuple[list[Session], dict[UUID, set]]:
    """Load the session data conflict detection needs.

    Returns one representative session per block (fully eager-loaded with
    teachers, rooms and class-subjects) together with the set of weeks each
    block spans. Sessions of a block are identical across weeks, so a single
    representative suffices while hydrating ~14x fewer rows than loading every
    week. Shared by the live-conflict and preview flows so both load data the
    same way.
    """
    dao = SessionDAO(db_session)
    sessions = dao.get_block_representatives(includes=list(SessionDAO.Include))
    return sessions, dao.get_block_weeks()


def load_red_blocks(db_session: DBSession) -> RedBlocks:
    """Load all teacher, room and class red blocks indexed by resource and weekday.

    Reads only the ``(resource_id, weekday, hour)`` columns rather than
    hydrating full ORM objects — there can be tens of thousands of red blocks
    (one row per 30-minute slot per resource) and that hydration dominated this
    step otherwise.
    """
    red_blocks = RedBlocks()
    for resource_id, weekday, hour in db_session.execute(
        select(TeacherRedBlock.teacher_id, TeacherRedBlock.weekday, TeacherRedBlock.hour),
    ).all():
        red_blocks.teacher.setdefault(resource_id, {}).setdefault(weekday, set()).add(hour)
    for resource_id, weekday, hour in db_session.execute(
        select(RoomRedBlock.room_id, RoomRedBlock.weekday, RoomRedBlock.hour),
    ).all():
        red_blocks.room.setdefault(resource_id, {}).setdefault(weekday, set()).add(hour)
    for resource_id, weekday, hour in db_session.execute(
        select(ClassRedBlock.class_id, ClassRedBlock.weekday, ClassRedBlock.hour),
    ).all():
        red_blocks.class_.setdefault(resource_id, {}).setdefault(weekday, set()).add(hour)
    return red_blocks


def _hhmm_to_minutes(hhmm: int) -> int:
    return (hhmm // 100) * 60 + (hhmm % 100)


def _session_hits_red_block(session: Session, slots: dict[WeekDay, set[int]]) -> bool:
    """True if the session's time range overlaps any 30-minute red block slot."""
    day_slots = slots.get(session.weekday)
    if not day_slots:
        return False
    start = _hhmm_to_minutes(session.start_time)
    end = start + session.duration * 30
    return any(
        start < _hhmm_to_minutes(hour) + RED_BLOCK_SLOT_MINUTES and _hhmm_to_minutes(hour) < end
        for hour in day_slots
    )


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


def _compute_conflict_rows(
    sessions: list[Session],
    red_blocks: RedBlocks | None = None,
    block_weeks: dict[UUID, set] | None = None,
) -> ConflictData:
    """Compute rows for the 6 normalized conflict tables.

    Returns a ConflictData with one entry per unique conflict_id in
    conflict_rows, plus junction rows for sessions, teachers, rooms, and
    classes. Sessions must have teachers, rooms, and session_class_subjects
    (with subject and class_ sub-relationships) eagerly loaded.

    The conflict_id is derived from the sorted block IDs of the group so all
    resource types that involve the same sessions share the same conflict_id.

    When ``red_blocks`` is given, sessions that overlap a teacher, room or
    class red block (an unavailable time slot) are also reported as conflicts.
    Each such conflict involves a single session, so its conflict_id —
    derived from that one block — never collides with a multi-session overlap.

    ``block_weeks`` maps each ``original_block_id`` to the set of weeks it
    occurs in; two blocks can only conflict if they share a week. When omitted
    it is derived from ``sessions``, which assumes the passed sessions span
    every week. Callers that pass a single representative session per block
    (to avoid hydrating every week) must supply ``block_weeks`` explicitly.
    """
    data = ConflictData()
    seen_conflict_ids: set[UUID] = set()
    seen_session_pairs: set[tuple[UUID, UUID]] = set()
    seen_resource_pairs: set[tuple[UUID, UUID]] = set()

    if block_weeks is None:
        block_weeks = defaultdict(set)
        for s in sessions:
            block_weeks[s.original_block_id].add(s.week)

    def _emit_group(
        group: list[Session],
        resource_id: UUID,
        resource_type: str,
        *,
        is_red_block: bool = False,
    ) -> None:
        conflict_id = UUID(_group_conflict_id([s.original_block_id for s in group]))
        if conflict_id not in seen_conflict_ids:
            seen_conflict_ids.add(conflict_id)
            data.conflict_rows.append({"conflict_id": conflict_id})
        if is_red_block:
            data.redblock_conflict_ids.add(str(conflict_id))
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

    # --- Red-block conflicts (resource unavailable during the session) ---
    if red_blocks is not None:
        for session in _dedup_by_block(sessions):
            for teacher in session.teachers:
                if _session_hits_red_block(session, red_blocks.teacher.get(teacher.id, {})):
                    _emit_group([session], teacher.id, "teacher_id", is_red_block=True)
            for room in session.rooms:
                if _session_hits_red_block(session, red_blocks.room.get(room.id, {})):
                    _emit_group([session], room.id, "room_id", is_red_block=True)
            seen_class_ids: set[UUID] = set()
            for cs in session.session_class_subjects:
                if cs.class_ is None or cs.class_id in seen_class_ids:
                    continue
                seen_class_ids.add(cs.class_id)
                if _session_hits_red_block(session, red_blocks.class_.get(cs.class_id, {})):
                    _emit_group([session], cs.class_id, "class_id", is_red_block=True)

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

        subjects = sorted(
            {
                cs.subject.acronym
                for s in sessions
                for cs in s.session_class_subjects
                if cs.subject is not None
            },
        )

        degrees: set[str] = set()
        for s in sessions:
            for cs in s.session_class_subjects:
                # A subject can span several years, so the degree is taken from
                # the class' year rather than the subject's.
                year = getattr(cs.class_, "year", None)
                degree = getattr(year, "degree", None)
                if degree is not None:
                    degrees.add(degree.acronym)

        is_red_block = cid in data.redblock_conflict_ids

        reasons: list[str] = []
        for teacher_id in teacher_ids_by_conflict.get(cid, []):
            teacher = teacher_map.get(teacher_id)
            if teacher:
                reasons.append(
                    f"Prof. {teacher.name} num horário indisponível (bloco vermelho)"
                    if is_red_block
                    else f"Prof. {teacher.name} em aulas diferentes ao mesmo tempo",
                )
        for room_id in room_ids_by_conflict.get(cid, []):
            room = room_map.get(room_id)
            if room:
                reasons.append(
                    f"Sala {room.name} num horário indisponível (bloco vermelho)"
                    if is_red_block
                    else f"Sala {room.name} com aulas diferentes ao mesmo tempo",
                )
        for class_id in class_ids_by_conflict.get(cid, []):
            class_ = class_map.get(class_id)
            if class_:
                reasons.append(
                    f"Turma {class_.code} num horário indisponível (bloco vermelho)"
                    if is_red_block
                    else f"Turma {class_.code} em aulas diferentes ao mesmo tempo",
                )

        results.append(
            ConflictResult(
                id=cid,
                event_ids=[str(s.id) for s in sessions],
                event_names=[_session_name(s) for s in sessions],
                day=first.weekday.value,
                time=first.start_time,
                turma=turma,
                block_ids=sorted({str(s.original_block_id) for s in sessions}),
                degrees=sorted(degrees),
                subjects=subjects,
                conflict_reasons=reasons,
            ),
        )

    return results


def get_live_conflicts(
    db_session: DBSession,
    sessions: list[Session] | None = None,
    block_weeks: dict[UUID, set] | None = None,
) -> list[ConflictResult]:
    """Detect conflicts from live session data and overlay any stored tags.

    When ``sessions`` is omitted, the representative sessions and per-block
    week sets are loaded via :func:`load_conflict_sessions`. Callers that
    already hold this data (e.g. the preview flow) pass both ``sessions`` and
    ``block_weeks`` to avoid reloading.

    Sessions must have teachers, rooms, and session_class_subjects (with subject
    and class_ sub-relationships) eagerly loaded. ``block_weeks`` maps each
    block to the weeks it spans so cross-block overlap detection works even when
    ``sessions`` holds one representative per block rather than every week.
    """
    if sessions is None:
        sessions, block_weeks = load_conflict_sessions(db_session)
    data = _compute_conflict_rows(sessions, load_red_blocks(db_session), block_weeks=block_weeks)
    results = _conflict_data_to_results(data, sessions)

    tag_assignments = ConflictDAO(db_session).get_tag_assignments()
    for result in results:
        result.tags = tag_assignments.get(result.id, [])

    return results
