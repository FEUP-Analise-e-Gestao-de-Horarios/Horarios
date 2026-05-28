import datetime
import tempfile
import uuid
from http import HTTPStatus
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from sqlalchemy import func, select

from src.projects.models import Project
from src.projects.projects_db.models import (
    Class,
    Degree,
    Room,
    Session,
    SessionClassSubject,
    Subject,
    Teacher,
    Year,
)
from src.projects.projects_db.models._secondary_tables import (
    session_rooms,
    session_teachers,
)
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.services.project_db import create_project_db, delete_project_db


class SessionDeletionEndpointTests(TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(PROJECTS_DB_PATH=Path(self.tmpdir.name))
        self.settings_override.enable()
        settings.SECRET_KEY = "test-secret-key"

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="session-delete@test.com",
            username="session-delete",
            password="test-password",
            is_active=True,
        )
        self.client.force_login(self.user)

        self.project = Project.objects.create(
            name="Deletion Test Project",
            url="https://example.com/project",
            creator=self.user,
        )
        create_project_db(self.project.pk)

        (
            self.session_id,
            self.room_id,
            self.teacher_id,
        ) = self._create_project_session_graph()

    def tearDown(self) -> None:
        delete_project_db(self.project.pk)
        self.settings_override.disable()
        self.tmpdir.cleanup()
        super().tearDown()

    def _create_project_session_graph(self) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
        with get_project_session(general_db(self.project.pk)) as db_session:
            degree = Degree(acronym="LEI", name="Informatics Engineering")
            year = Year(number=1, degree=degree)
            subject = Subject(
                number=1,
                code="TEST001",
                acronym="TEST",
                name="Testing Subject",
                year=year,
            )
            class_ = Class(code="1LEIC01", shift=1, year=year)
            room = Room(name="B001", type=None, size=None, seats=None)
            teacher = Teacher(number=1, acronym="ABC", name="Alice Example")
            project_session = Session(
                week=datetime.date(2026, 1, 5),
                weekday=WeekDay.MONDAY,
                start_time=8,
                duration=2,
                type="T",
                original_block_id=uuid.uuid7(),
                rooms=[room],
                teachers=[teacher],
                session_class_subjects=[
                    SessionClassSubject(class_=class_, subject=subject),
                ],
            )

            db_session.add_all([degree, room, teacher, project_session])
            db_session.commit()

            return project_session.id, room.id, teacher.id

    def test_delete_session_endpoint_removes_session_and_its_links(self) -> None:
        response = self.client.delete(
            f"/api/projects/{self.project.pk}/sessions/{self.session_id}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json(),
            {"message": "Session deleted successfully"},
        )

        with get_project_session(general_db(self.project.pk)) as db_session:
            self.assertIsNone(db_session.get(Session, self.session_id))
            self.assertIsNotNone(db_session.get(Room, self.room_id))
            self.assertIsNotNone(db_session.get(Teacher, self.teacher_id))
            self.assertEqual(
                db_session.scalar(select(func.count()).select_from(SessionClassSubject)),
                0,
            )
            self.assertEqual(db_session.execute(select(session_rooms)).all(), [])
            self.assertEqual(db_session.execute(select(session_teachers)).all(), [])

    def test_delete_session_endpoint_returns_404_for_missing_session(self) -> None:
        response = self.client.delete(
            f"/api/projects/{self.project.pk}/sessions/{uuid.uuid7()}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(
            response.json(),
            {
                "error": "projects.sessions.not_found",
                "message": "Session not found.",
            },
        )
