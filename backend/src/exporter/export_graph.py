from typing import Any

import networkx as nx

from src.projects.projects_db.dao.base_dao import ChangedRecords
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session


class ExportGraph:
    def __init__(self, changes: ChangedRecords, project_id: int):
        self.changes = changes
        self.dependency_graph: nx.DiGraph | None = None

        with get_session(general_db(project_id)) as session:
            session_dao = SessionDAO(session)
            self.sessions_by_id = {}
            self.sessions_by_change_key = {}

            for db_session in session_dao.get_all():
                session_data = {
                    "id": db_session.id,
                    "start_time": db_session.start_time,
                    "duration": db_session.duration,
                    "rooms": [room.name for room in db_session.rooms],
                    "teachers": [teacher.number for teacher in db_session.teachers],
                    "classes": [
                        session_class_subject.class_.code
                        for session_class_subject in db_session.session_class_subjects
                    ],
                }

                self.sessions_by_id[db_session.id] = session_data
                self.sessions_by_change_key[self.normalize_id(db_session.id)] = session_data

    @staticmethod
    def convert_to_minutes(time: int | str) -> int:
        if isinstance(time, str) and ":" in time:
            hours, minutes = time.split(":", maxsplit=1)
            return int(hours) * 60 + int(minutes)

        time = int(time)
        return time // 100 * 60 + time % 100

    @staticmethod
    def normalize_id(value) -> str:
        return str(value).replace("-", "")

    @staticmethod
    def get_time_slots(start_time: int | str, duration: int) -> list[int]:
        start_time = ExportGraph.convert_to_minutes(start_time)
        return [start_time + i * 30 for i in range(int(duration))]

    @staticmethod
    def add_session_to_resource_graph(
        graph: nx.DiGraph,
        resources: list[str | int],
        session_id,
        time_slots: list[int],
    ):
        for resource in resources:
            for time_slot in time_slots:
                node = (resource, time_slot)
                if not graph.has_node(node):
                    graph.add_node(node, ids=[])

                graph.nodes[node]["ids"].append(session_id)

    @staticmethod
    def is_column_change(change: Any) -> bool:
        return isinstance(change, dict) and "old" in change and "new" in change

    @staticmethod
    def add_time_change_edges(
        graph: nx.DiGraph,
        resources: list[str | int],
        session_id,
        old_time_slots: list[int],
        new_time_slots: list[int],
    ):
        for resource in resources:
            for old_time_slot, new_time_slot in zip(old_time_slots, new_time_slots, strict=False):
                old_node = (resource, old_time_slot)
                new_node = (resource, new_time_slot)

                if not graph.has_node(old_node):
                    graph.add_node(old_node, ids=[])

                if not graph.has_node(new_node):
                    graph.add_node(new_node, ids=[])

                if not graph.has_edge(old_node, new_node):
                    graph.add_edge(old_node, new_node, ids=[])

                graph.edges[old_node, new_node]["ids"].append(session_id)

    def connect_nodes_according_to_changes(self, graphs: dict[str, nx.DiGraph]):
        for session_id, changes in self.changes.items():
            start_time_change = changes.get("start_time")
            if not self.is_column_change(start_time_change):
                continue

            session_data = self.sessions_by_change_key.get(self.normalize_id(session_id))
            if session_data is None:
                continue

            duration = int(session_data["duration"])
            old_time_slots = self.get_time_slots(start_time_change["old"], duration)
            new_time_slots = self.get_time_slots(start_time_change["new"], duration)

            self.add_time_change_edges(
                graphs["rooms"],
                session_data["rooms"],
                session_data["id"],
                old_time_slots,
                new_time_slots,
            )
            self.add_time_change_edges(
                graphs["teachers"],
                session_data["teachers"],
                session_data["id"],
                old_time_slots,
                new_time_slots,
            )
            self.add_time_change_edges(
                graphs["classes"],
                session_data["classes"],
                session_data["id"],
                old_time_slots,
                new_time_slots,
            )

    def build_change_dependency_graph(
        self,
        graphs: dict[str, nx.DiGraph],
    ) -> nx.DiGraph:
        dependency_graph = nx.DiGraph()
        change_key_by_session_id = {
            self.normalize_id(session_id): session_id for session_id in self.changes
        }

        dependency_graph.add_nodes_from(self.changes.keys())

        for resource_graph in graphs.values():
            for old_node, _new_node, edge_data in resource_graph.edges(data=True):
                moving_sessions = edge_data.get("ids", [])
                final_slot_sessions = resource_graph.nodes[old_node].get("ids", [])

                for moving_session_id in moving_sessions:
                    moving_change_key = change_key_by_session_id.get(
                        self.normalize_id(moving_session_id),
                    )
                    if moving_change_key is None:
                        continue

                    for final_slot_session_id in final_slot_sessions:
                        final_slot_change_key = change_key_by_session_id.get(
                            self.normalize_id(final_slot_session_id),
                        )
                        if (
                            final_slot_change_key is None
                            or final_slot_change_key == moving_change_key
                        ):
                            continue

                        dependency_graph.add_edge(
                            moving_change_key,
                            final_slot_change_key,
                        )

        return dependency_graph

    def order_change_groups_using_graph(
        self,
    ) -> list[list[Any]]:
        if self.dependency_graph is None:
            self.build_graph()

        dependency_graph = self.dependency_graph
        assert dependency_graph is not None
        components = list(nx.strongly_connected_components(dependency_graph))
        condensed_graph = nx.condensation(dependency_graph, components)

        return [
            self.sort_group_by_classes(condensed_graph.nodes[component]["members"])
            for component in self.topological_sort_by_classes(condensed_graph)
        ]

    def build_modification_steps(
        self,
    ) -> list[dict[str, Any]]:
        if self.dependency_graph is None:
            self.build_graph()

        assert self.dependency_graph is not None
        return [
            {
                "type": "exchange" if len(group) > 1 else "move",
                "sessions": [str(session_id) for session_id in group],
            }
            for group in self.order_change_groups_using_graph()
        ]

    def get_session_classes(self, session_id: Any) -> tuple[str, ...]:
        session_data = self.sessions_by_change_key.get(self.normalize_id(session_id), {})
        return tuple(
            sorted(str(class_code) for class_code in session_data.get("classes", [])),
        )

    def get_group_classes(self, group: set[Any] | list[Any]) -> tuple[str, ...]:
        classes: set[str] = set()

        for session_id in group:
            classes.update(self.get_session_classes(session_id))

        return tuple(sorted(classes))

    def sort_group_by_classes(self, group: set[Any]) -> list[Any]:
        return sorted(
            group,
            key=lambda session_id: (
                self.get_session_classes(session_id),
                str(session_id),
            ),
        )

    def topological_sort_by_classes(self, condensed_graph: nx.DiGraph) -> list[Any]:
        """Topologically sort dependency groups while keeping classes clustered."""
        in_degrees = dict(condensed_graph.in_degree())
        ready = [node for node, degree in in_degrees.items() if degree == 0]
        ordered = []
        previous_classes: set[str] = set()

        while ready:
            ready.sort(
                key=lambda component: self.class_priority_key(
                    condensed_graph.nodes[component]["members"],
                    previous_classes,
                ),
            )
            component = ready.pop(0)
            ordered.append(component)
            previous_classes = set(
                self.get_group_classes(condensed_graph.nodes[component]["members"]),
            )

            for successor in condensed_graph.successors(component):
                in_degrees[successor] -= 1
                if in_degrees[successor] == 0:
                    ready.append(successor)

        if len(ordered) != condensed_graph.number_of_nodes():
            raise nx.NetworkXUnfeasible("Dependency graph contains a cycle.")

        return ordered

    def class_priority_key(
        self,
        group: set[Any],
        previous_classes: set[str],
    ) -> tuple[int, tuple[str, ...], tuple[str, ...]]:
        group_classes = self.get_group_classes(group)
        class_overlap = len(previous_classes.intersection(group_classes))

        return (
            -class_overlap,
            group_classes,
            tuple(sorted(str(session_id) for session_id in group)),
        )

    def build_graph(self):
        room_graph = nx.DiGraph()
        teacher_graph = nx.DiGraph()
        class_graph = nx.DiGraph()

        for session_id, session_data in self.sessions_by_id.items():
            time_slots = self.get_time_slots(
                session_data["start_time"],
                session_data["duration"],
            )

            self.add_session_to_resource_graph(
                room_graph,
                session_data["rooms"],
                session_id,
                time_slots,
            )
            self.add_session_to_resource_graph(
                teacher_graph,
                session_data["teachers"],
                session_id,
                time_slots,
            )
            self.add_session_to_resource_graph(
                class_graph,
                session_data["classes"],
                session_id,
                time_slots,
            )

        graphs = {
            "rooms": room_graph,
            "teachers": teacher_graph,
            "classes": class_graph,
        }

        self.connect_nodes_according_to_changes(graphs)
        self.dependency_graph = self.build_change_dependency_graph(graphs)
        return graphs

    def get_dependencies(
        self,
        *,
        transitive: bool = False,
    ) -> dict[Any, list[Any]]:
        """Return prerequisite changes for each changed-session node."""
        if self.dependency_graph is None:
            self.build_graph()

        assert self.dependency_graph is not None
        dependencies = {}

        for node in self.dependency_graph.nodes:
            if transitive:
                node_dependencies = nx.ancestors(self.dependency_graph, node)
            else:
                node_dependencies = self.dependency_graph.predecessors(node)

            dependencies[node] = sorted(node_dependencies, key=str)

        return dependencies
