from sqlalchemy import func, select

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.dao.conflict_resource_dao import (
    ConflictResourceColumn,
    ConflictResourceDAO,
    ConflictResourceJoin,
    ConflictResourceSpec,
)
from src.projects.projects_db.models._secondary_tables import session_teachers
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.teacher import Teacher
from src.projects.projects_db.models.teacher_red_block import TeacherRedBlock
from src.projects.projects_db.schemas.teacher import TeacherConflict, TeacherStats


class TeacherDAO(BaseDAO[Teacher]):
    """Data access object for Teacher records."""

    def __init__(self, session: Session, *, flush_on_create: bool = True) -> None:
        super().__init__(Teacher, session, flush_on_create=flush_on_create)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, *, number: int, acronym: str, name: str) -> Teacher:
        """Create and persist a new teacher.

        Args:
            number: Unique institutional number of the teacher.
            acronym: Short abbreviation identifying the teacher.
            name: Full name of the teacher.

        Returns:
            The newly created Teacher instance, flushed to the session.
        """
        return self._create(number=number, acronym=acronym, name=name)

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_with_stats(self) -> list[TeacherStats]:
        """Return all teachers with their subject, class, session, and red-block counts.

        Counts default to 0 when a teacher has no associated records.

        Returns:
            A list of TeacherStats, one per teacher, in an unspecified order.
        """
        sessions_sq = (
            select(
                session_teachers.c.teacher_id,
                func.count(SessionClassSubject.subject_id.distinct()).label("subjects"),
                func.count(SessionClassSubject.class_id.distinct()).label("classes"),
                func.count(session_teachers.c.session_id.distinct()).label("sessions"),
            )
            .select_from(session_teachers)
            .outerjoin(
                SessionClassSubject,
                SessionClassSubject.session_id == session_teachers.c.session_id,
            )
            .group_by(session_teachers.c.teacher_id)
            .subquery()
        )
        red_blocks_sq = (
            select(TeacherRedBlock.teacher_id, func.count().label("cnt"))
            .group_by(TeacherRedBlock.teacher_id)
            .subquery()
        )

        rows = self.session.execute(
            select(
                Teacher.id,
                Teacher.number,
                Teacher.acronym,
                Teacher.name,
                func.coalesce(sessions_sq.c.subjects, 0).label("subjects"),
                func.coalesce(sessions_sq.c.classes, 0).label("classes"),
                func.coalesce(sessions_sq.c.sessions, 0).label("sessions"),
                func.coalesce(red_blocks_sq.c.cnt, 0).label("red_blocks"),
            )
            .outerjoin(sessions_sq, sessions_sq.c.teacher_id == Teacher.id)
            .outerjoin(red_blocks_sq, red_blocks_sq.c.teacher_id == Teacher.id),
        ).all()

        return [TeacherStats.model_validate(row, from_attributes=True) for row in rows]

    def get_conflicting_slots(self) -> list[TeacherConflict]:
        """Return overlapping teacher allocations grouped into conflict windows.

        Each result represents one overlapping window for a teacher on a given
        week and weekday. The returned ``start_time`` and ``duration`` span the
        full conflicting window, and ``session_ids`` contains every session in
        that overlap cluster.
        """
        rows = ConflictResourceDAO(self.session).get_conflicting_slots(
            ConflictResourceSpec(
                model=Teacher,
                id_column=ConflictResourceColumn("teacher_id", Teacher.id),
                identifying_columns=(
                    ConflictResourceColumn("teacher_number", Teacher.number),
                    ConflictResourceColumn("teacher_acronym", Teacher.acronym),
                    ConflictResourceColumn("teacher_name", Teacher.name),
                ),
                joins=(
                    ConflictResourceJoin(
                        session_teachers,
                        session_teachers.c.teacher_id == Teacher.id,
                    ),
                    ConflictResourceJoin(
                        Session,
                        Session.id == session_teachers.c.session_id,
                    ),
                ),
            ),
        )

        return [TeacherConflict(**row) for row in rows]
