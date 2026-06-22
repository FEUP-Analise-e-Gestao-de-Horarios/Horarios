import datetime
import json
import tempfile
import uuid
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from sqlalchemy import func, select

from src.exporter.compact_payload import COMPACT_EXPORT_FORMAT, expand_compact_export_payload
from src.projects.models import Project
from src.projects.projects_db.dao import ExportCacheDAO
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
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.projects_db.registry import init_engine
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
        init_engine(initial_db(self.project.pk))

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

    def test_export_endpoint_reuses_cached_compact_payload(self) -> None:
        response = self.client.post(
            f"/api/projects/{self.project.pk}/export",
            data=json.dumps({"recalculate_export_graph": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["message"], "Project export computed successfully")
        self.assertEqual(response.json()["data"]["format"], COMPACT_EXPORT_FORMAT)

        with patch(
            "src.projects.views.export.RoomDAO.get_conflicting_slots",
            side_effect=AssertionError("export conflicts should have been cached"),
        ):
            cached_response = self.client.post(
                f"/api/projects/{self.project.pk}/export",
                data=json.dumps({"recalculate_export_graph": False}),
                content_type="application/json",
            )

        self.assertEqual(cached_response.status_code, HTTPStatus.OK)
        self.assertEqual(cached_response.json()["message"], "Project export loaded from cache")
        self.assertEqual(cached_response.json()["data"], response.json()["data"])

    def test_export_endpoint_replaces_legacy_expanded_cache(self) -> None:
        with get_project_session(general_db(self.project.pk)) as db_session:
            ExportCacheDAO(db_session).replace_project_export_payload(
                {
                    "added_removed_sessions": {"added": [], "removed": []},
                    "rooms_conflicts": [],
                    "teacher_conflicts": [],
                    "classes_conflicts": [],
                    "modification_steps": [],
                },
            )
            db_session.commit()

        response = self.client.post(
            f"/api/projects/{self.project.pk}/export",
            data=json.dumps({"recalculate_export_graph": False}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["message"], "Project export computed successfully")
        self.assertEqual(response.json()["data"]["format"], COMPACT_EXPORT_FORMAT)

    def test_export_endpoint_supports_compact_payload_format(self) -> None:
        expanded_response = self.client.post(
            f"/api/projects/{self.project.pk}/export",
            data=json.dumps({"recalculate_export_graph": True, "payload_format": "expanded"}),
            content_type="application/json",
        )
        compact_response = self.client.post(
            f"/api/projects/{self.project.pk}/export",
            data=json.dumps({"payload_format": "compact"}),
            content_type="application/json",
        )

        self.assertEqual(expanded_response.status_code, HTTPStatus.OK)
        self.assertEqual(compact_response.status_code, HTTPStatus.OK)
        compact_payload = compact_response.json()["data"]
        self.assertEqual(compact_payload["format"], COMPACT_EXPORT_FORMAT)
        self.assertEqual(
            expand_compact_export_payload(compact_payload).model_dump(mode="json"),
            expanded_response.json()["data"],
        )

    def test_export_endpoint_includes_class_conflict_subject_labels(self) -> None:
        with get_project_session(general_db(self.project.pk)) as db_session:
            existing_session = db_session.get(Session, self.session_id)
            self.assertIsNotNone(existing_session)
            assert existing_session is not None

            class_subject = existing_session.session_class_subjects[0]
            conflict_session = Session(
                week=existing_session.week,
                weekday=existing_session.weekday,
                start_time=9,
                duration=2,
                type="T",
                original_block_id=uuid.uuid7(),
                rooms=list(existing_session.rooms),
                teachers=list(existing_session.teachers),
                session_class_subjects=[
                    SessionClassSubject(
                        class_=class_subject.class_,
                        subject=class_subject.subject,
                    ),
                ],
            )
            db_session.add(conflict_session)
            db_session.commit()

        response = self.client.post(
            f"/api/projects/{self.project.pk}/export",
            data=json.dumps({"recalculate_export_graph": True, "payload_format": "expanded"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json()["data"]["rooms_conflicts"][0]["subject_labels"],
            ["TEST (TEST001)"],
        )
        self.assertEqual(
            response.json()["data"]["teacher_conflicts"][0]["subject_labels"],
            ["TEST (TEST001)"],
        )
        self.assertEqual(
            response.json()["data"]["classes_conflicts"][0]["subject_labels"],
            ["TEST (TEST001)"],
        )

    def test_export_generation_does_not_load_all_sessions(self) -> None:
        with patch(
            "src.projects.projects_db.dao.base_dao.BaseDAO.get_all",
            side_effect=AssertionError("export generation should use scoped loaders"),
        ):
            response = self.client.post(
                f"/api/projects/{self.project.pk}/export",
                data=json.dumps({"recalculate_export_graph": True}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_teachers_endpoint_includes_red_block_count(self) -> None:
        response = self.client.get(f"/api/projects/{self.project.pk}/teachers/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["message"], "Teachers retrieved successfully")
        self.assertEqual(
            response.json()["data"]["teachers"],
            [
                {
                    "id": str(self.teacher_id),
                    "number": 1,
                    "acronym": "ABC",
                    "name": "Alice Example",
                    "subjects": 1,
                    "classes": 1,
                    "sessions": 1,
                    "red_blocks": 0,
                },
            ],
        )

    def test_delete_session_endpoint_clears_export_cache(self) -> None:
        response = self.client.post(
            f"/api/projects/{self.project.pk}/export",
            data=json.dumps({"recalculate_export_graph": False}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        with get_project_session(general_db(self.project.pk)) as db_session:
            self.assertIsNotNone(ExportCacheDAO(db_session).get_project_export_payload())

        delete_response = self.client.delete(
            f"/api/projects/{self.project.pk}/sessions/{self.session_id}",
        )
        self.assertEqual(delete_response.status_code, HTTPStatus.OK)

        with get_project_session(general_db(self.project.pk)) as db_session:
            self.assertIsNone(ExportCacheDAO(db_session).get_project_export_payload())
