"""Response schemas for the Session entity."""

from typing import TYPE_CHECKING, Self
from uuid import UUID

from src.projects.views.schemas.shared import (
    ClassBase,
    RoomBase,
    SessionBase,
    SubjectBase,
    TeacherBase,
)

if TYPE_CHECKING:
    from src.projects.projects_db.models import Session


class SessionResponse(SessionBase):
    """A session enriched with its full teacher, subject, class and room lists."""

    rooms: list[RoomBase]
    teachers: list[TeacherBase]
    subjects: list[SubjectBase]
    classes: list[ClassBase]

    @classmethod
    def from_session(cls, session: Session) -> Self:
        """Build a SessionResponse from an eagerly-loaded Session ORM instance.

        Deduplicates subjects and classes across the session's
        ``session_class_subjects`` rows, since the same subject or class may
        appear in more than one pairing.
        """
        seen_subjects: dict[UUID, object] = {}
        seen_classes: dict[UUID, object] = {}
        for scs in session.session_class_subjects:
            seen_subjects[scs.subject_id] = scs.subject
            seen_classes[scs.class_id] = scs.class_

        return cls.model_validate(
            {
                "id": session.id,
                "original_block_id": session.original_block_id,
                "week": session.week,
                "weekday": session.weekday,
                "start_time": session.start_time,
                "duration": session.duration,
                "type": session.type,
                "rooms": list(session.rooms),
                "teachers": list(session.teachers),
                "subjects": list(seen_subjects.values()),
                "classes": list(seen_classes.values()),
            },
        )
