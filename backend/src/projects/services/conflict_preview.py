"""Conflict-preview service: hypothetical session change → solved/new conflicts."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.services.conflict_detection import (
    _compute_conflict_rows,
    _conflict_data_to_results,
    get_live_conflicts,
    load_red_blocks,
)
from src.projects.services.schemas.conflicts import (
    ConflictData,
    ConflictResult,
    SimulatedClassSubject,
    SimulatedSession,
)


def preview_conflict_changes(
    db_session: DBSession,
    original_block_id: UUID,
    new_weekday: WeekDay,
    new_start_time: int,
    new_duration: int,
    new_teacher_ids: list[UUID],
    new_room_ids: list[UUID],
    new_class_ids: list[UUID] | None = None,
) -> tuple[list[ConflictResult], list[ConflictResult]]:
    """Return (solved, new) conflict lists for a hypothetical block edit.

    Runs conflict detection only over the sessions relevant to the changed
    block (sharing its new teachers, rooms, or classes on the new weekday)
    rather than the full session set.

    Args:
        db_session: Active project database session.
        original_block_id: The block whose values are hypothetically changed.
        new_weekday: Proposed weekday for the block.
        new_start_time: Proposed start time in HHMM format (e.g. 1430).
        new_duration: Proposed duration in 30-minute units.
        new_teacher_ids: Proposed teacher UUIDs.
        new_room_ids: Proposed room UUIDs.

    Returns:
        A tuple (solved, new) where:
        - solved: live ConflictResult objects that would disappear.
        - new: ConflictResult objects that would be created.
    """
    includes = list(SessionDAO.Include)
    session_dao = SessionDAO(db_session)

    # 1. Load all sessions to compute the current live conflict state.
    all_sessions = session_dao.get_all(includes=includes)
    block_sessions = [s for s in all_sessions if s.original_block_id == original_block_id]
    if not block_sessions:
        return [], []

    block_session_ids: set[UUID] = {s.id for s in block_sessions}

    # 2. Find live conflicts that currently involve any session in this block.
    all_live = get_live_conflicts(db_session, all_sessions)
    current_for_block = [
        c for c in all_live if any(UUID(eid) in block_session_ids for eid in c.event_ids)
    ]
    current_conflict_ids: set[str] = {c.id for c in current_for_block}

    # 3. Build index maps from already-loaded sessions — no extra DB queries needed.
    sessions_by_teacher: dict[UUID, list] = defaultdict(list)
    sessions_by_room: dict[UUID, list] = defaultdict(list)
    sessions_by_class: dict[UUID, list] = defaultdict(list)
    teacher_map: dict[UUID, object] = {}
    room_map: dict[UUID, object] = {}
    class_map: dict[UUID, object] = {}
    for s in all_sessions:
        for t in s.teachers:
            sessions_by_teacher[t.id].append(s)
            teacher_map[t.id] = t
        for r in s.rooms:
            sessions_by_room[r.id].append(s)
            room_map[r.id] = r
        for cs in s.session_class_subjects:
            if cs.class_ is not None:
                sessions_by_class[cs.class_id].append(s)
                class_map[cs.class_id] = cs.class_

    # Build a lookup of existing class-subject pairs from the block.
    existing_scs: dict[UUID, object] = {}
    for s in block_sessions:
        for cs in s.session_class_subjects:
            if cs.class_id not in existing_scs:
                existing_scs[cs.class_id] = cs

    # Use new_class_ids when provided; otherwise fall back to existing block classes.
    effective_class_ids: set[UUID] = (
        set(new_class_ids) if new_class_ids is not None else set(existing_scs)
    )

    # Collect candidate sessions sharing the new resources, excluding the block itself.
    seen_session_ids: set[UUID] = set()
    candidates: list = []

    def _add_candidates(sessions: list) -> None:
        for s in sessions:
            if s.id not in seen_session_ids and s.original_block_id != original_block_id:
                seen_session_ids.add(s.id)
                candidates.append(s)

    for teacher_id in new_teacher_ids:
        _add_candidates(sessions_by_teacher.get(teacher_id, []))
    for room_id in new_room_ids:
        _add_candidates(sessions_by_room.get(room_id, []))
    for class_id in effective_class_ids:
        _add_candidates(sessions_by_class.get(class_id, []))

    # 4. Extract Teacher and Room ORM objects from the index.
    new_teachers = [teacher_map[tid] for tid in new_teacher_ids if tid in teacher_map]
    new_rooms = [room_map[rid] for rid in new_room_ids if rid in room_map]

    # 5. Build simulated session_class_subjects when new_class_ids is provided.
    simulated_scs: list | None = None
    if new_class_ids is not None:
        fallback_cs = next(iter(existing_scs.values()), None)
        fallback_subject_id = getattr(fallback_cs, "subject_id", None)
        fallback_subject = getattr(fallback_cs, "subject", None)

        simulated_scs = []
        for class_id in new_class_ids:
            if class_id in existing_scs:
                simulated_scs.append(existing_scs[class_id])
            elif class_id in class_map and fallback_subject_id is not None:
                simulated_scs.append(
                    SimulatedClassSubject(
                        class_id=class_id,
                        subject_id=fallback_subject_id,
                        class_=class_map[class_id],
                        subject=fallback_subject,
                    ),
                )

    # 6. Build simulated sessions — same block/weeks, new slot+resources+classes.
    simulated = [
        SimulatedSession(
            id=s.id,
            week=s.week,
            weekday=new_weekday,
            start_time=new_start_time,
            duration=new_duration,
            type=s.type,
            original_block_id=original_block_id,
            teachers=new_teachers,
            rooms=new_rooms,
            session_class_subjects=simulated_scs
            if simulated_scs is not None
            else s.session_class_subjects,
        )
        for s in block_sessions
    ]

    # 7. Run detection over candidates + simulated block.
    data = _compute_conflict_rows(candidates + simulated, load_red_blocks(db_session))

    # 8. Extract conflict IDs that involve the simulated block.
    new_conflict_ids_for_block: set[str] = {
        str(row["conflict_id"])
        for row in data.session_rows
        if row["session_id"] in block_session_ids
    }

    # 9. Diff against current live conflicts.
    truly_solved_ids = current_conflict_ids - new_conflict_ids_for_block
    truly_new_ids = new_conflict_ids_for_block - current_conflict_ids

    solved = [c for c in current_for_block if c.id in truly_solved_ids]

    new_data = ConflictData(
        conflict_rows=[r for r in data.conflict_rows if str(r["conflict_id"]) in truly_new_ids],
        session_rows=[r for r in data.session_rows if str(r["conflict_id"]) in truly_new_ids],
        teacher_rows=[r for r in data.teacher_rows if str(r["conflict_id"]) in truly_new_ids],
        room_rows=[r for r in data.room_rows if str(r["conflict_id"]) in truly_new_ids],
        class_rows=[r for r in data.class_rows if str(r["conflict_id"]) in truly_new_ids],
        redblock_conflict_ids=data.redblock_conflict_ids & truly_new_ids,
    )
    new = _conflict_data_to_results(new_data, candidates + simulated)

    return solved, new
