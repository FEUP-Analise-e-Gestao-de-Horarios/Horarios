from unittest import TestCase

import networkx as nx

from src.exporter.compact_payload import compact_export_payload, expand_compact_export_payload
from src.exporter.export_graph import ExportGraph
from src.exporter.schemas import ProjectExportPayload


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
