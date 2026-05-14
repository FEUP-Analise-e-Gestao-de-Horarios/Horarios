from typing import Any

import networkx as nx

from src.exporter.export_graph_types import (
    RESOURCE_SPECS,
    Resource,
    ResourceMovement,
    ResourceSpec,
    TimeMovement,
    TimePlacement,
)
from src.projects.projects_db.dao.base_dao import ChangedRecords
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session


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
                session_data = self.serialize_session(db_session)
                self.sessions_by_id[db_session.id] = session_data
                self.sessions_by_change_key[self.normalize_id(db_session.id)] = session_data

    def serialize_session(self, db_session: Session) -> dict[str, Any]:
        """Return session data used by the exporter and its resource graphs."""
        return {
            "id": db_session.id,
            "start_time": db_session.start_time,
            "duration": db_session.duration,
            "weekday": db_session.weekday,
            "week": db_session.week,
            "room_ids": tuple(self.normalize_id(room.id) for room in db_session.rooms),
            "rooms": [room.name for room in db_session.rooms],
            "teacher_ids": tuple(self.normalize_id(teacher.id) for teacher in db_session.teachers),
            "teachers": [teacher.number for teacher in db_session.teachers],
            "class_ids": tuple(
                sorted(
                    {
                        self.normalize_id(session_class_subject.class_id)
                        for session_class_subject in db_session.session_class_subjects
                    },
                ),
            ),
            "classes": [
                session_class_subject.class_.code
                for session_class_subject in db_session.session_class_subjects
            ],
        }

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
    def get_time_slots(start_time: int | str, duration: int) -> tuple[int, ...]:
        """Return every 30-minute slot occupied by a session."""
        start_time = ExportGraph.convert_to_minutes(start_time)
        return tuple(start_time + i * 30 for i in range(int(duration)))

    @staticmethod
    def add_session_to_resource_graph(
        graph: nx.DiGraph,
        resources: tuple[Resource, ...],
        session_id: Any,
        placement: TimePlacement,
    ):
        """Add the current occupied slots for one session to a resource graph.

        Resource graph nodes have the shape ``(resource, time_slot, weekday, week)``.
        Each node stores the session ids currently occupying that resource slot.
        """
        for resource in resources:
            for time_slot in placement.time_slots:
                node = placement.node(resource, time_slot)
                if not graph.has_node(node):
                    graph.add_node(node, ids=[])

                graph.nodes[node]["ids"].append(session_id)

    @staticmethod
    def is_column_change(change: Any) -> bool:
        """Check whether a diff entry contains an ``old`` and ``new`` value."""
        return isinstance(change, dict) and "old" in change and "new" in change

    @staticmethod
    def is_relation_change(change: Any) -> bool:
        """Check whether a diff entry contains added or removed relation rows."""
        return isinstance(change, dict) and (
            bool(change.get("added")) or bool(change.get("removed"))
        )

    @staticmethod
    def add_change_edges(
        graph: nx.DiGraph,
        session_id: Any,
        resources: ResourceMovement,
        time: TimeMovement,
        include_shared_resources: bool,
    ):
        """Add directed movement edges for one session in a resource graph.

        An edge from the old slot to the new slot means the session wants to
        leave the old slot and occupy the new slot for that resource.
        """
        for old_resource, new_resource in resources.pairs(include_shared_resources):
            for old_time_slot, new_time_slot in zip(
                time.old.time_slots,
                time.new.time_slots,
                strict=False,
            ):
                old_node = time.old.node(old_resource, old_time_slot)
                new_node = time.new.node(new_resource, new_time_slot)

                if not graph.has_node(old_node):
                    graph.add_node(old_node, ids=[])

                if not graph.has_node(new_node):
                    graph.add_node(new_node, ids=[])

                if not graph.has_edge(old_node, new_node):
                    graph.add_edge(old_node, new_node, ids=[])

                graph.edges[old_node, new_node]["ids"].append(session_id)

    @staticmethod
    def get_relation_ids(
        change: Any,
        change_type: str,
        id_key: str,
    ) -> set[str]:
        """Extract normalized relation ids from an added/removed diff bucket."""
        if not isinstance(change, dict):
            return set()

        return {
            ExportGraph.normalize_id(row[id_key])
            for row in change.get(change_type, [])
            if id_key in row
        }

    def get_old_resources(
        self,
        current_resources: tuple[Resource, ...],
        change: Any,
        id_key: str,
    ) -> tuple[Resource, ...]:
        """Reconstruct old resources from current resources and relation diffs."""
        current = {self.normalize_id(resource) for resource in current_resources}
        if not self.is_relation_change(change):
            return tuple(sorted(current))

        added = self.get_relation_ids(change, "added", id_key)
        removed = self.get_relation_ids(change, "removed", id_key)

        return tuple(sorted((current - added) | removed))

    def build_current_placement(self, session_data: dict[str, Any]) -> TimePlacement:
        """Build the current time placement for a session snapshot."""
        return TimePlacement(
            time_slots=self.get_time_slots(
                session_data["start_time"],
                session_data["duration"],
            ),
            weekday=session_data["weekday"],
            week=session_data["week"],
        )

    def build_time_movement(
        self,
        session_data: dict[str, Any],
        changes: dict[str, Any],
    ) -> TimeMovement:
        """Build old/new time placement for a changed session."""
        start_time_change = changes.get("start_time")
        weekday_change = changes.get("weekday")
        week_change = changes.get("week")
        duration_change = changes.get("duration")

        old_start_time = (
            start_time_change["old"]
            if self.is_column_change(start_time_change)
            else session_data["start_time"]
        )
        old_duration = (
            duration_change["old"]
            if self.is_column_change(duration_change)
            else session_data["duration"]
        )
        old_weekday = (
            weekday_change["old"]
            if self.is_column_change(weekday_change)
            else session_data["weekday"]
        )
        old_week = (
            week_change["old"] if self.is_column_change(week_change) else session_data["week"]
        )

        return TimeMovement(
            old=TimePlacement(
                time_slots=self.get_time_slots(old_start_time, old_duration),
                weekday=old_weekday,
                week=old_week,
            ),
            new=self.build_current_placement(session_data),
            changed=any(
                self.is_column_change(changes.get(field))
                for field in ("start_time", "weekday", "week", "duration")
            ),
        )

    def build_resource_movement(
        self,
        session_data: dict[str, Any],
        changes: dict[str, Any],
        spec: ResourceSpec,
    ) -> ResourceMovement:
        """Build old/new resource sets for one resource kind."""
        current_resources = session_data[spec.session_field]

        return ResourceMovement(
            old=self.get_old_resources(
                current_resources,
                changes.get(spec.relation_field),
                spec.id_key,
            ),
            new=current_resources,
        )

    def connect_nodes_according_to_changes(self, graphs: dict[str, nx.DiGraph]):
        """Create movement edges for changed session times or resources.

        The method updates the room, teacher, and class graphs in-place. If a
        session also changed week or weekday, the edge starts at the old date
        coordinates and ends at the current session coordinates. Resource-only
        changes are represented as edges from old resources to new resources at
        the same time coordinates.
        """
        for session_id, changes in self.changes.items():
            session_data = self.sessions_by_change_key.get(
                self.normalize_id(session_id),
            )
            if session_data is None:
                continue

            time = self.build_time_movement(session_data, changes)
            for spec in RESOURCE_SPECS:
                resources = self.build_resource_movement(
                    session_data,
                    changes,
                    spec,
                )
                self.add_change_edges_if_needed(
                    graphs[spec.graph_name],
                    session_data["id"],
                    resources,
                    time,
                )

    def add_change_edges_if_needed(
        self,
        graph: nx.DiGraph,
        session_id: Any,
        resources: ResourceMovement,
        time: TimeMovement,
    ) -> None:
        """Add graph edges when either time coordinates or resources changed."""
        if not time.changed and not resources.changed:
            return

        self.add_change_edges(
            graph,
            session_id,
            resources,
            time,
            include_shared_resources=time.changed,
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
                        "modifications": self.changes[session_id],
                        "dependencies": dependencies[session_id],
                        "session": self.get_public_session_data(session_id),
                    }
                    for session_id in group
                },
            }
            for group in self.order_change_groups_using_graph()
        ]

    def get_public_session_data(self, session_id: Any) -> dict[str, Any]:
        """Return session data without graph-only resource id fields."""
        session_data = dict(self.sessions_by_change_key[self.normalize_id(session_id)])

        for field in ("room_ids", "teacher_ids", "class_ids"):
            session_data.pop(field, None)

        return session_data

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
        graphs = {spec.graph_name: nx.DiGraph() for spec in RESOURCE_SPECS}

        for session_id, session_data in self.sessions_by_id.items():
            placement = self.build_current_placement(session_data)

            for spec in RESOURCE_SPECS:
                self.add_session_to_resource_graph(
                    graphs[spec.graph_name],
                    session_data[spec.session_field],
                    session_id,
                    placement,
                )

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
