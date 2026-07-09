import datetime
import json
import tempfile
import uuid
from pathlib import Path
from unittest import TestCase

import networkx as nx
from django.conf import settings
from django.test import override_settings

from src.exporter.benchmark_runtime import BenchmarkCounts, ExportBenchmarkResult
from src.exporter.benchmark_scaling import (
    MutationSummary,
    ScalingRunRecord,
    build_scaling_artifact,
    copy_project_tree,
    count_changed_sessions,
    ensure_clean_exporter_baseline,
    mutate_project_for_benchmark,
    write_scaling_artifacts,
)
from src.exporter.compact_payload import compact_export_payload, expand_compact_export_payload
from src.exporter.export_graph import ExportGraph
from src.exporter.schemas import ProjectExportPayload
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
from src.projects.projects_db.paths import general_db, initial_db, project_dir
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.projects_db.registry import init_engine
from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.services.project_db import create_project_db, delete_project_db


class ExportGraphExchangeClassificationTests(TestCase):
    def build_graph(self, start_times: dict[str, tuple[int, int]]) -> ExportGraph:
        graph = ExportGraph.__new__(ExportGraph)
        graph.changes = {
            session_id: {"start_time": {"old": old_start_time, "new": new_start_time}}
            for session_id, (old_start_time, new_start_time) in start_times.items()
        }
        graph.sessions_by_change_key = {
            session_id: {
                "id": session_id,
                "start_time": new_start_time,
                "duration": 2,
                "weekday": "monday",
                "week": "2026-01-05",
                "classes": [session_id],
            }
            for session_id, (_old_start_time, new_start_time) in start_times.items()
        }
        graph.dependency_graph = nx.DiGraph()
        graph.dependency_graph.add_edges_from([("a", "b"), ("b", "a")])
        return graph

    def test_exact_time_swap_is_exchange(self) -> None:
        graph = self.build_graph({"a": (830, 1000), "b": (1000, 830)})

        self.assertEqual(
            graph.get_graph_ordered_modifications(),
            [("a", "exchange"), ("b", "exchange")],
        )

    def test_offset_time_cycle_is_move(self) -> None:
        graph = self.build_graph({"a": (830, 1030), "b": (1000, 830)})

        self.assertEqual(
            graph.get_graph_ordered_modifications(),
            [("a", "move"), ("b", "move")],
        )


class ExportGraphWeekScopeTests(TestCase):
    def build_graph(self, changed_session_ids: list[str]) -> ExportGraph:
        graph = ExportGraph.__new__(ExportGraph)
        graph.changes = {
            session_id: {"start_time": {"old": 830, "new": 1000}}
            for session_id in changed_session_ids
        }
        graph.initial_sessions = {
            "a": {
                "id": "a",
                "original_block_id": "block",
                "week": "2026-01-05",
                "start_time": 830,
                "duration": 2,
                "weekday": "monday",
                "rooms": [],
                "teachers": [],
                "classes": [],
                "subjects": [],
            },
            "b": {
                "id": "b",
                "original_block_id": "block",
                "week": "2026-01-12",
                "start_time": 830,
                "duration": 2,
                "weekday": "monday",
                "rooms": [],
                "teachers": [],
                "classes": [],
                "subjects": [],
            },
        }
        return graph

    def test_marks_change_as_all_weeks_when_block_is_fully_changed(self) -> None:
        graph = self.build_graph(["a", "b"])

        group = graph.build_session_group(["a", "b"], {"a": [], "b": []})

        self.assertTrue(group["applies_to_all_weeks"])

    def test_marks_change_as_partial_when_only_some_block_weeks_change(self) -> None:
        graph = self.build_graph(["a"])

        group = graph.build_session_group(["a"], {"a": []})

        self.assertFalse(group["applies_to_all_weeks"])


class CompactExportPayloadTests(TestCase):
    def build_payload(self, modifications: dict) -> dict:
        return {
            "added_removed_sessions": {"added": [], "removed": []},
            "rooms_conflicts": [],
            "teacher_conflicts": [],
            "classes_conflicts": [],
            "modification_steps": [
                {
                    "type": "move",
                    "original_block_id": "block-1",
                    "session_ids": ["session-1"],
                    "weeks": ["2026-01-05"],
                    "week_range": {
                        "start": "2026-01-05",
                        "end": "2026-01-05",
                        "contiguous": True,
                    },
                    "applies_to_all_weeks": False,
                    "modifications": modifications,
                    "dependencies": [],
                    "session": {
                        "id": "session-1",
                        "original_block_id": "block-1",
                        "start_time": 8,
                        "duration": 2,
                        "weekday": "monday",
                        "week": "2026-01-05",
                        "rooms": [],
                        "teachers": [],
                        "classes": [],
                        "subjects": [],
                    },
                },
            ],
        }

    def test_compact_export_skips_absent_optional_modification_fields(self) -> None:
        payload = self.build_payload({"start_time": {"old": 8, "new": 10}})

        compact = compact_export_payload(payload).model_dump(mode="json")

        self.assertEqual(
            compact["modification_steps"][0]["modifications"],
            {"start_time": {"old": 8, "new": 10}},
        )
        self.assertEqual(
            expand_compact_export_payload(compact).model_dump(mode="json"),
            ProjectExportPayload.model_validate(payload).model_dump(mode="json"),
        )

    def test_compact_export_preserves_nested_null_column_values(self) -> None:
        payload = self.build_payload({"week": {"old": None, "new": "2026-01-12"}})

        compact = compact_export_payload(payload).model_dump(mode="json")

        self.assertEqual(
            compact["modification_steps"][0]["modifications"],
            {"week": {"old": None, "new": "2026-01-12"}},
        )

    def test_compact_export_preserves_class_conflict_subject_labels(self) -> None:
        payload = self.build_payload({})
        payload["classes_conflicts"] = [
            {
                "class_id": "class-1",
                "class_code": "1LEIC01",
                "subject_labels": ["IA (IA001)"],
                "week": "2026-01-05",
                "weeks": ["2026-01-05"],
                "weekday": "monday",
                "start_time": 830,
                "duration": 2,
                "collisions": 2,
                "session_ids": ["session-1", "session-2"],
            },
        ]

        compact = compact_export_payload(payload).model_dump(mode="json")

        self.assertEqual(
            compact["conflicts"][0][9],
            ["IA (IA001)"],
        )
        self.assertEqual(
            expand_compact_export_payload(compact).model_dump(mode="json"),
            ProjectExportPayload.model_validate(payload).model_dump(mode="json"),
        )

    def test_expand_compact_export_resolves_normalized_entity_ids(self) -> None:
        hyphenated_session_id = "019e21c0-8ed5-7722-bd5e-8ad5a3c750b3"
        normalized_session_id = "019e21c08ed57722bd5e8ad5a3c750b3"

        expanded = expand_compact_export_payload(
            {
                "format": "compact_export_v1",
                "entities": {
                    "rooms": {},
                    "teachers": {},
                    "classes": {
                        "019e21c0-8ed5-7722-bd5e-8ad5a3c750c4": {
                            "class_code": "1LEIC01",
                        },
                    },
                    "subjects": {
                        "019e21c0-8ed5-7722-bd5e-8ad5a3c750d5": {
                            "subject_acronym": "IA",
                        },
                    },
                    "sessions": {
                        hyphenated_session_id: {
                            "id": hyphenated_session_id,
                            "start_time": 830,
                            "duration": 2,
                            "weekday": "monday",
                            "week": "2026-01-05",
                            "rooms": [],
                            "teachers": [],
                            "classes": ["1LEIC01"],
                            "subjects": [
                                {
                                    "name": "Inteligencia Artificial",
                                    "acronym": "IA",
                                    "code": "IA001",
                                },
                            ],
                        },
                    },
                },
                "added_removed_sessions": {"added": [], "removed": []},
                "conflicts": [],
                "modification_steps": [
                    {
                        "type": "move",
                        "original_block_id": "block-1",
                        "session_ids": [normalized_session_id],
                        "weeks": ["2026-01-05"],
                        "week_range": {
                            "start": "2026-01-05",
                            "end": "2026-01-05",
                            "contiguous": True,
                        },
                        "applies_to_all_weeks": False,
                        "modifications": {
                            "class_subjects": {
                                "added": [
                                    [
                                        "019e21c08ed57722bd5e8ad5a3c750c4",
                                        "019e21c08ed57722bd5e8ad5a3c750d5",
                                    ],
                                ],
                                "removed": [],
                            },
                        },
                        "dependencies": [],
                    },
                ],
            },
        ).model_dump(mode="json")

        step = expanded["modification_steps"][0]
        self.assertEqual(step["session"]["start_time"], 830)
        self.assertEqual(step["session"]["classes"], ["1LEIC01"])
        self.assertEqual(
            step["modifications"]["class_subjects"]["added"][0]["class_code"],
            "1LEIC01",
        )
        self.assertEqual(
            step["modifications"]["class_subjects"]["added"][0]["subject_acronym"],
            "IA",
        )


class ExportBenchmarkScalingTests(TestCase):
    project_id = 1

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(PROJECTS_DB_PATH=Path(self.tmpdir.name))
        self.settings_override.enable()
        settings.SECRET_KEY = "test-secret-key"

        create_project_db(self.project_id)
        init_engine(initial_db(self.project_id))
        self._seed_project_db(general_db(self.project_id))
        self._seed_project_db(initial_db(self.project_id))

    def tearDown(self) -> None:
        delete_project_db(self.project_id)
        self.settings_override.disable()
        self.tmpdir.cleanup()
        super().tearDown()

    @staticmethod
    def _stable_uuid(value: int) -> uuid.UUID:
        return uuid.UUID(int=value + 1)

    def _seed_project_db(self, db_path: Path) -> None:
        with get_project_session(db_path) as db_session:
            degree = Degree(
                id=self._stable_uuid(10),
                acronym="LEI",
                name="Informatics Engineering",
            )
            year = Year(
                id=self._stable_uuid(11),
                number=1,
                degree=degree,
            )
            subjects = [
                Subject(
                    id=self._stable_uuid(20 + index),
                    number=index + 1,
                    code=f"SUB{index + 1:03d}",
                    acronym=f"S{index + 1}",
                    name=f"Subject {index + 1}",
                    years=[year],
                )
                for index in range(2)
            ]
            classes = [
                Class(
                    id=self._stable_uuid(30 + index),
                    code=f"1LEIC0{index + 1}",
                    shift=index + 1,
                    year=year,
                )
                for index in range(2)
            ]
            rooms = [
                Room(
                    id=self._stable_uuid(40 + index),
                    name=f"B10{index}",
                    type=None,
                    size=None,
                    seats=None,
                )
                for index in range(4)
            ]
            teachers = [
                Teacher(
                    id=self._stable_uuid(50 + index),
                    number=index + 1,
                    acronym=f"T{index + 1}",
                    name=f"Teacher {index + 1}",
                )
                for index in range(4)
            ]

            db_session.add_all([degree, year, *subjects, *classes, *rooms, *teachers])
            base_date = datetime.date(2026, 1, 5)
            for index in range(12):
                subject = subjects[index % len(subjects)]
                class_ = classes[index % len(classes)]
                session_obj = Session(
                    id=self._stable_uuid(100 + index),
                    week=base_date + datetime.timedelta(days=7 * (index // 2)),
                    weekday=WeekDay.MONDAY if index % 2 == 0 else WeekDay.TUESDAY,
                    start_time=800 + (index % 4) * 100,
                    duration=2,
                    type="T",
                    original_block_id=self._stable_uuid(200 + index),
                    rooms=[rooms[index % len(rooms)]],
                    teachers=[teachers[index % len(teachers)]],
                    session_class_subjects=[
                        SessionClassSubject(
                            class_=class_,
                            subject=subject,
                        ),
                    ],
                )
                db_session.add(session_obj)
            db_session.commit()

    def test_mutation_produces_requested_changed_session_count(self) -> None:
        ensure_clean_exporter_baseline(self.project_id, projects_db_path=Path(self.tmpdir.name))

        summary = mutate_project_for_benchmark(
            self.project_id,
            changed_sessions=5,
            seed=1234,
            projects_db_path=Path(self.tmpdir.name),
        )

        self.assertEqual(summary.requested_changed_sessions, 5)
        self.assertEqual(summary.actual_changed_sessions, 5)
        self.assertEqual(summary.added_sessions, 1)
        self.assertEqual(summary.removed_sessions, 1)
        self.assertEqual(len(summary.modified_session_ids), 5)
        self.assertEqual(
            count_changed_sessions(self.project_id, projects_db_path=Path(self.tmpdir.name)),
            5,
        )

    def test_mutation_is_deterministic_for_same_seed(self) -> None:
        source_project_dir = project_dir(self.project_id)
        copy_a_root = Path(self.tmpdir.name) / "copy-a"
        copy_b_root = Path(self.tmpdir.name) / "copy-b"
        copy_project_tree(source_project_dir, copy_a_root, self.project_id)
        copy_project_tree(source_project_dir, copy_b_root, self.project_id)

        summary_a = mutate_project_for_benchmark(
            self.project_id,
            changed_sessions=4,
            seed=777,
            projects_db_path=copy_a_root,
        )
        summary_b = mutate_project_for_benchmark(
            self.project_id,
            changed_sessions=4,
            seed=777,
            projects_db_path=copy_b_root,
        )

        self.assertEqual(summary_a.to_dict(), summary_b.to_dict())

    def test_scaling_artifact_serialization_writes_expected_fields(self) -> None:
        mutation = MutationSummary(
            requested_changed_sessions=5,
            actual_changed_sessions=5,
            added_sessions=1,
            removed_sessions=1,
            modified_session_ids=["a", "b", "c", "d", "e"],
            added_session_ids=["f"],
            removed_session_ids=["g"],
            seed=1234,
        )
        benchmark = ExportBenchmarkResult(
            project_id=1,
            projects_db_path=str(Path(self.tmpdir.name)),
            recalculate=True,
            payload_format="compact",
            cache_hit=False,
            counts=BenchmarkCounts(
                changed_sessions=5,
                modification_steps=3,
                room_conflicts=1,
                teacher_conflicts=1,
                class_conflicts=0,
                added_sessions=1,
                removed_sessions=1,
            ),
            payload_kb={"compact": 2.5, "expanded": 4.0},
            response_payload_kb=2.7,
            timings_ms={"build_modification_steps": 10.0, "room_conflicts": 6.0},
            total_ms=30.0,
        )
        record = ScalingRunRecord(
            requested_changed_sessions=5,
            actual_changed_sessions=5,
            run_number=1,
            mutation=mutation,
            benchmark=benchmark,
        )
        artifact = build_scaling_artifact(
            source_project="project_id:1",
            source_project_dir=project_dir(self.project_id),
            sizes=[5],
            repetitions=1,
            seed=1234,
            recalculate=True,
            payload_format="compact",
            records=[record],
            git_commit="abc123",
        )

        output_dir = Path(self.tmpdir.name) / "artifacts"
        json_path, csv_path = write_scaling_artifacts(artifact, output_dir)

        self.assertTrue(json_path.exists())
        self.assertTrue(csv_path.exists())
        loaded = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertIn("runs", loaded)
        self.assertIn("summaries", loaded)
        csv_text = csv_path.read_text(encoding="utf-8")
        self.assertIn("requested_changed_sessions", csv_text)
        self.assertIn("median_total_ms", csv_text)
