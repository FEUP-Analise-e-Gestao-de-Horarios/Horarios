from sqlalchemy import CTE, func, select

from src.projects.projects_db.models import Session, SessionClassSubject


def candidate_blocks_cte() -> CTE:
    """Return a CTE that identifies all original_block_ids belonging to a parallel candidate group.

    Blocks with at least two distinct members in a group are treated as candidates.
    """
    session_subjects = (
        select(
            Session.original_block_id,
            func.min(Session.week).over(partition_by=Session.original_block_id).label("first_week"),
            Session.weekday,
            Session.start_time,
            SessionClassSubject.subject_id,
        )
        .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
        .distinct()
        .cte("session_subjects")
    )

    sized = select(
        session_subjects.c.original_block_id,
        session_subjects.c.first_week,
        session_subjects.c.weekday.label("group_weekday"),
        session_subjects.c.start_time.label("group_start_time"),
        session_subjects.c.subject_id.label("group_subject_id"),
        func.count()
        .over(
            partition_by=[
                session_subjects.c.first_week,
                session_subjects.c.weekday,
                session_subjects.c.start_time,
                session_subjects.c.subject_id,
            ],
        )
        .label("group_size"),
    ).cte("sized")

    return (
        select(
            sized.c.original_block_id,
            sized.c.first_week,
            sized.c.group_weekday,
            sized.c.group_start_time,
            sized.c.group_subject_id,
        )
        .where(sized.c.group_size > 1)
        .cte("candidate_blocks")
    )
