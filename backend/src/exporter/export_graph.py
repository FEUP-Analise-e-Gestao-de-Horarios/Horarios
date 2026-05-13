from datetime import date
from typing import Any

import networkx as nx

from src.projects.projects_db.dao.base_dao import ChangedRecords
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session
from src.projects.projects_db.schemas.weekday import WeekDay


class ExportGraph:
    """Build dependency-aware export steps for modified timetable sessions."""

    def __init__(self, changes: ChangedRecords, project_id: int):
        """Load modified sessions and the current timetable data for a project.

        Args:
            changes: Field-level changes keyed by session id.
            project_id: Project whose general database should be inspected.
        """
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
                    "weekday": db_session.weekday,
                    "week": db_session.week,
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
        """Convert an ``HHMM`` or ``HH:MM`` time value into minutes after midnight."""
        if isinstance(time, str) and ":" in time:
            hours, minutes = time.split(":", maxsplit=1)
            return int(hours) * 60 + int(minutes)

        time = int(time)
        return time // 100 * 60 + time % 100

    @staticmethod
    def normalize_id(value) -> str:
        """Return an id string without hyphens so UUID forms can be compared."""
        return str(value).replace("-", "")

    @staticmethod
    def get_time_slots(start_time: int | str, duration: int) -> list[int]:
        """Return every 30-minute slot occupied by a session."""
        start_time = ExportGraph.convert_to_minutes(start_time)
        return [start_time + i * 30 for i in range(int(duration))]

    @staticmethod
    def add_session_to_resource_graph(
        graph: nx.DiGraph,
        resources: list[str | int],
        session_id,
        time_slots: list[int],
        weekday: WeekDay,
        week: date,
    ):
        """Add the current occupied slots for one session to a resource graph.

        Resource graph nodes have the shape ``(resource, time_slot, weekday, week)``.
        Each node stores the session ids currently occupying that resource slot.
        """
        for resource in resources:
            for time_slot in time_slots:
                node = (resource, time_slot, str(weekday), str(week))
                if not graph.has_node(node):
                    graph.add_node(node, ids=[])

                graph.nodes[node]["ids"].append(session_id)

    @staticmethod
    def is_column_change(change: Any) -> bool:
        """Check whether a diff entry contains an ``old`` and ``new`` value."""
        return isinstance(change, dict) and "old" in change and "new" in change

    @staticmethod
    def add_time_change_edges(
        graph: nx.DiGraph,
        resources: list[str | int],
        session_id,
        old_time_slots: list[int],
        new_time_slots: list[int],
        old_weekday: WeekDay | str,
        old_week: date | str,
        new_weekday: WeekDay | str,
        new_week: date | str,
    ):
        """Add directed movement edges for one session in a resource graph.

        An edge from the old slot to the new slot means the session wants to
        leave the old slot and occupy the new slot for that resource.
        """
        for resource in resources:
            for old_time_slot, new_time_slot in zip(
                old_time_slots,
                new_time_slots,
                strict=False,
            ):
                old_node = (resource, old_time_slot, str(old_weekday), str(old_week))
                new_node = (resource, new_time_slot, str(new_weekday), str(new_week))

                if not graph.has_node(old_node):
                    graph.add_node(old_node, ids=[])

                if not graph.has_node(new_node):
                    graph.add_node(new_node, ids=[])

                if not graph.has_edge(old_node, new_node):
                    graph.add_edge(old_node, new_node, ids=[])

                graph.edges[old_node, new_node]["ids"].append(session_id)

    def connect_nodes_according_to_changes(self, graphs: dict[str, nx.DiGraph]):
        """Create resource movement edges for every changed session start time.

        The method updates the room, teacher, and class graphs in-place. If a
        session also changed week or weekday, the edge starts at the old date
        coordinates and ends at the current session coordinates.
        """
        for session_id, changes in self.changes.items():
            start_time_change = changes.get("start_time")
            if not self.is_column_change(start_time_change):
                continue

            session_data = self.sessions_by_change_key.get(
                self.normalize_id(session_id),
            )
            if session_data is None:
                continue

            duration = int(session_data["duration"])
            old_time_slots = self.get_time_slots(start_time_change["old"], duration)
            new_time_slots = self.get_time_slots(start_time_change["new"], duration)
            weekday_change = changes.get("weekday")
            week_change = changes.get("week")
            old_weekday = (
                weekday_change["old"]
                if self.is_column_change(weekday_change)
                else session_data["weekday"]
            )
            old_week = (
                week_change["old"] if self.is_column_change(week_change) else session_data["week"]
            )

            self.add_time_change_edges(
                graphs["rooms"],
                session_data["rooms"],
                session_data["id"],
                old_time_slots,
                new_time_slots,
                old_weekday,
                old_week,
                session_data["weekday"],
                session_data["week"],
            )
            self.add_time_change_edges(
                graphs["teachers"],
                session_data["teachers"],
                session_data["id"],
                old_time_slots,
                new_time_slots,
                old_weekday,
                old_week,
                session_data["weekday"],
                session_data["week"],
            )
            self.add_time_change_edges(
                graphs["classes"],
                session_data["classes"],
                session_data["id"],
                old_time_slots,
                new_time_slots,
                old_weekday,
                old_week,
                session_data["weekday"],
                session_data["week"],
            )

    def build_change_dependency_graph(
        self,
        graphs: dict[str, nx.DiGraph],
    ) -> nx.DiGraph:
        """Build a graph where each node is a changed session.

        Edge direction is ``moving_change -> blocking_change``: if session A
        wants to move into a slot currently occupied by changed session B, A
        depends on B moving first. Cycles therefore represent exchanges.
        """
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
        """Return changed sessions in dependency order, grouped by exchanges.

        Strongly connected components are returned as one group because their
        sessions mutually depend on each other. Independent groups are sorted
        topologically and then class-aware to reduce timetable context switches.
        """
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
        """Return export-ready modification steps with dependencies and session data."""
        if self.dependency_graph is None:
            self.build_graph()

        assert self.dependency_graph is not None

        dependencies = self.get_dependencies()
        return [
            {
                "type": "exchange" if len(group) > 1 else "move",
                "sessions": {
                    str(session_id): {
                        "modifications": self.changes[str(session_id)],
                        "dependencies": dependencies[str(session_id)],
                        "session": self.sessions_by_change_key[str(session_id)],
                    }
                    for session_id in group
                },
            }
            for group in self.order_change_groups_using_graph()
        ]

    def get_session_classes(self, session_id: Any) -> tuple[str, ...]:
        """Return sorted class codes for a session id."""
        session_data = self.sessions_by_change_key.get(
            self.normalize_id(session_id),
            {},
        )
        return tuple(
            sorted(str(class_code) for class_code in session_data.get("classes", [])),
        )

    def get_group_classes(self, group: set[Any] | list[Any]) -> tuple[str, ...]:
        """Return sorted class codes touched by a group of session ids."""
        classes: set[str] = set()

        for session_id in group:
            classes.update(self.get_session_classes(session_id))

        return tuple(sorted(classes))

    def sort_group_by_classes(self, group: set[Any]) -> list[Any]:
        """Sort sessions inside one dependency group by class, then by id."""
        return sorted(
            group,
            key=lambda session_id: (
                self.get_session_classes(session_id),
                str(session_id),
            ),
        )

    def topological_sort_by_classes(self, condensed_graph: nx.DiGraph) -> list[Any]:
        """Topologically sort dependency groups while keeping classes clustered.

        At each step this chooses from the currently dependency-safe groups.
        The preferred group is the one sharing the most classes with the group
        emitted immediately before it.
        """
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
        """Return a stable sort key that prefers class continuity."""
        group_classes = self.get_group_classes(group)
        class_overlap = len(previous_classes.intersection(group_classes))

        return (
            -class_overlap,
            group_classes,
            tuple(sorted(str(session_id) for session_id in group)),
        )

    def build_graph(self):
        """Build resource graphs and cache the resulting change dependency graph.

        Returns:
            A dictionary with room, teacher, and class resource graphs.
        """
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
                session_data["weekday"],
                session_data["week"],
            )
            self.add_session_to_resource_graph(
                teacher_graph,
                session_data["teachers"],
                session_id,
                time_slots,
                session_data["weekday"],
                session_data["week"],
            )
            self.add_session_to_resource_graph(
                class_graph,
                session_data["classes"],
                session_id,
                time_slots,
                session_data["weekday"],
                session_data["week"],
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
        """Return prerequisite changes for each changed-session node.

        Args:
            transitive: If false, include only direct prerequisites. If true,
                include the full chain of prerequisites.
        """
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
