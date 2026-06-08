from unittest import TestCase

import networkx as nx

from src.exporter.export_graph import ExportGraph


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
