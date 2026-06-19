from collections.abc import Iterable, Mapping
from itertools import combinations
from typing import Any

import networkx as nx

from src.exporter.legacy.conflicts import (
    class_conflicts,
    room_conflicts,
    serialize_conflicts,
    sessions_conflict,
    teacher_conflicts,
)
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session


class Comparator:
    """Legacy exporter comparator for full DB diffing and conflict ordering."""

    def __init__(self, proj_id: int):
        """Open initial and current project DB sessions for comparison."""
        self.proj_id = proj_id
        self.general_session_db = get_session(general_db(proj_id))
        self.initial_session_db = get_session(initial_db(proj_id))
        self.changes_dict = {}

    def __enter__(self):
        """Return the comparator for use as a context manager."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Close both project DB sessions when leaving the context manager."""
        self.general_session_db.close()
        self.initial_session_db.close()

    def _get_session_maps(self) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        """Load diff-friendly session maps from initial and current databases."""
        session_dao_initial = SessionDAO(self.initial_session_db)
        session_dao_general = SessionDAO(self.general_session_db)

        old_map = session_dao_initial.get_diff_map()
        current_map = session_dao_general.get_diff_map()
        return old_map, current_map

    def database_differences(self) -> dict[str, Any]:
        """Return added, removed, and modified sessions between DB snapshots."""
        old_map, current_map = self._get_session_maps()

        current_ids = set(current_map.keys())
        old_ids = set(old_map.keys())

        # 1. Added & Removed
        added = {id_: current_map[id_] for id_ in (current_ids - old_ids)}
        removed = {id_: old_map[id_] for id_ in (old_ids - current_ids)}

        # 2. Modified (The "Delta")
        modified = {}
        for id_ in current_ids & old_ids:
            if current_map[id_] != old_map[id_]:
                diff = {
                    k: {"old": old_map[id_][k], "new": current_map[id_][k]}
                    for k in current_map[id_]
                    if current_map[id_][k] != old_map[id_][k]
                }
                modified[id_] = diff

        return {"added": added, "removed": removed, "modified": modified}

    def database_conflicts(self):
        """Return serialized room, class, and teacher conflicts for current sessions."""
        session_dao_general = SessionDAO(self.general_session_db)
        general_sessions = session_dao_general.get_all()

        return {
            "rooms_conflicts": serialize_conflicts(room_conflicts(general_sessions)),
            "classes_conflicts": serialize_conflicts(class_conflicts(general_sessions)),
            "teacher_conflicts": serialize_conflicts(teacher_conflicts(general_sessions)),
        }

    def build_order_graph(
        self,
        old_map: Mapping[str, Mapping[str, Any]],
        new_map: Mapping[str, Mapping[str, Any]],
        changed_ids: Iterable[str] | None = None,
    ) -> tuple[str, ...]:
        """Topologically order modified sessions when a conflict-free sequence exists."""
        if changed_ids is None:
            changed_session_ids = sorted(
                session_id
                for session_id in old_map.keys() & new_map.keys()
                if old_map[session_id] != new_map[session_id]
            )
        else:
            changed_session_ids = sorted(
                session_id
                for session_id in changed_ids
                if session_id in old_map and session_id in new_map
            )

        graph = nx.DiGraph()
        graph.add_nodes_from(changed_session_ids)

        for a_id, b_id in combinations(changed_session_ids, 2):
            old_a = old_map[a_id]
            new_a = new_map[a_id]
            old_b = old_map[b_id]
            new_b = new_map[b_id]

            old_old = sessions_conflict(old_a, old_b)
            new_old = sessions_conflict(new_a, old_b)
            old_new = sessions_conflict(old_a, new_b)
            new_new = sessions_conflict(new_a, new_b)

            if new_new and not old_old:
                raise ValueError(
                    f"No conflict-free final order exists for sessions {a_id} and {b_id}",
                )

            if new_old and not old_old:
                graph.add_edge(b_id, a_id)

            if old_new and not old_old:
                graph.add_edge(a_id, b_id)

        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("No conflict-free sequential order exists")

        return tuple(nx.topological_sort(graph))

    def get_modification_order(self) -> tuple[str, ...]:
        """Load session maps and return the legacy modification order."""
        old_map, current_map = self._get_session_maps()
        return self.build_order_graph(old_map, current_map)
