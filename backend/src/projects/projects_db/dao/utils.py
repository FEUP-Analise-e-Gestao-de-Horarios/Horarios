from sqlalchemy import func, select

from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject


# parallel_utils.py
def parallel_sessions_subquery():
    return (
        select(
            SessionClassSubject.session_id,
            SessionClassSubject.subject_id,
        )
        .join(Session, Session.id == SessionClassSubject.session_id)
        .where(Session.type != "T")
        .group_by(SessionClassSubject.session_id, SessionClassSubject.subject_id)
        .having(func.count(SessionClassSubject.class_id.distinct()) > 1)
    ).subquery()
