import itertools
from datetime import timedelta
from typing import cast
from uuid import UUID

import networkx as nx
from sqlalchemy.orm import Session as DBSession

from src.exporter.export_graph_loaders import ExportGraphSnapshotLoader, ResourceOccupancyLoader
from src.exporter.export_graph_types import (
    RESOURCE_SPECS,
    ChangeBucket,
    DependencyMap,
    ExportGraphStep,
    GraphPrimitive,
    GraphValue,
    Resource,
    ResourceMovement,
    ResourceNode,
    ResourceOccupancy,
    ResourceSpec,
    SessionChanges,
    SessionId,
    SessionSnapshot,
    TimeMovement,
    TimePlacement,
)
from src.exporter.export_graph_utils import (
    get_time_slots,
    jsonable,
    normalize_id,
    parse_week_date,
    to_uuid,
)
from src.exporter.schemas import ExportModificationStep, ExportSessionSnapshot
from src.projects.projects_db.dao.base_dao import ChangedRecords
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session


class ExportGraph:
    """Build dependency-aware export steps for modified timetable sessions."""

    def __init__(self, changes: ChangedRecords, project_id: int):
        """Load modified sessions and the current timetable data for a project.

        Args:
            changes: Field-level changes keyed by session id.
            project_id: Project whose general database should be inspected.
        """
        self.changes = cast(dict[SessionId, SessionChanges], changes)
        self.dependency_graph: nx.DiGraph | None = None

        session_ids = self.change_session_ids()
        with get_session(general_db(project_id)) as session:
            current_loader = ExportGraphSnapshotLoader(session)
            self.sessions_by_id = current_loader.load_sessions_by_id(session_ids)
            self.sessions_by_change_key = {
                normalize_id(session_id): session_data
                for session_id, session_data in self.sessions_by_id.items()
            }
            self.scoped_occupancy = self.load_scoped_occupancy(session)

        with get_session(initial_db(project_id)) as session:
            initial_loader = ExportGraphSnapshotLoader(session)
            initial_by_id = initial_loader.load_sessions_by_id(session_ids)
            self.initial_sessions = {
                normalize_id(session_id): session_data
                for session_id, session_data in initial_by_id.items()
            }
            self.original_block_weeks = initial_loader.load_original_block_weeks(
                {
                    session_data["original_block_id"]
                    for session_data in self.initial_sessions.values()
                    if session_data.get("original_block_id") is not None
                },
            )

    def change_session_ids(self) -> list[UUID]:
        """Return changed session ids in database UUID form."""
        return [to_uuid(session_id) for session_id in self.changes]

    @staticmethod
    def is_column_change(change: GraphValue | None) -> bool:
        """Check whether a diff entry contains an ``old`` and ``new`` value."""
        return isinstance(change, dict) and "old" in change and "new" in change

    @staticmethod
    def is_relation_change(change: GraphValue | None) -> bool:
        """Check whether a diff entry contains added or removed relation rows."""
        return isinstance(change, dict) and (
            bool(change.get("added")) or bool(change.get("removed"))
        )

    @staticmethod
    def add_change_edges(
        graph: nx.DiGraph,
        session_id: SessionId,
        resources: ResourceMovement,
        time: TimeMovement,
        include_shared_resources: bool,
    ) -> None:
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
        change: GraphValue | None,
        change_type: str,
        id_key: str,
    ) -> set[str]:
        """Extract normalized relation ids from an added/removed diff bucket."""
        if not isinstance(change, dict):
            return set()

        rows = cast(list[SessionSnapshot], change.get(change_type, []))
        return {normalize_id(row[id_key]) for row in rows if id_key in row}

    def get_old_resources(
        self,
        current_resources: tuple[Resource, ...],
        change: GraphValue | None,
        id_key: str,
    ) -> tuple[Resource, ...]:
        """Reconstruct old resources from current resources and relation diffs."""
        current = {normalize_id(resource) for resource in current_resources}
        if not self.is_relation_change(change):
            return tuple(sorted(current))

        added = self.get_relation_ids(change, "added", id_key)
        removed = self.get_relation_ids(change, "removed", id_key)

        return tuple(sorted((current - added) | removed))

    def build_current_placement(self, session_data: SessionSnapshot) -> TimePlacement:
        """Build the current time placement for a session snapshot."""
        return TimePlacement(
            time_slots=get_time_slots(
                cast(int | str, session_data["start_time"]),
                cast(int, session_data["duration"]),
            ),
            weekday=cast(str, session_data["weekday"]),
            week=cast(str, session_data["week"]),
        )

    def build_time_movement(
        self,
        session_data: SessionSnapshot,
        changes: SessionChanges,
    ) -> TimeMovement:
        """Build old/new time placement for a changed session."""
        start_time_change = changes.get("start_time")
        weekday_change = changes.get("weekday")
        week_change = changes.get("week")
        duration_change = changes.get("duration")

        start_time_bucket = cast(ChangeBucket, start_time_change)
        duration_bucket = cast(ChangeBucket, duration_change)
        weekday_bucket = cast(ChangeBucket, weekday_change)
        week_bucket = cast(ChangeBucket, week_change)
        old_start_time = (
            start_time_bucket["old"]
            if self.is_column_change(start_time_change)
            else session_data["start_time"]
        )
        old_duration = (
            duration_bucket["old"]
            if self.is_column_change(duration_change)
            else session_data["duration"]
        )
        old_weekday = (
            weekday_bucket["old"]
            if self.is_column_change(weekday_change)
            else session_data["weekday"]
        )
        old_week = (
            week_bucket["old"] if self.is_column_change(week_change) else session_data["week"]
        )

        return TimeMovement(
            old=TimePlacement(
                time_slots=get_time_slots(cast(int | str, old_start_time), cast(int, old_duration)),
                weekday=cast(str, old_weekday),
                week=cast(str, old_week),
            ),
            new=self.build_current_placement(session_data),
            changed=any(
                self.is_column_change(changes.get(field))
                for field in ("start_time", "weekday", "week", "duration")
            ),
        )

    def build_resource_movement(
        self,
        session_data: SessionSnapshot,
        changes: SessionChanges,
        spec: ResourceSpec,
    ) -> ResourceMovement:
        """Build old/new resource sets for one resource kind."""
        current_resources = cast(tuple[Resource, ...], session_data[spec.session_field])

        return ResourceMovement(
            old=self.get_old_resources(
                current_resources,
                changes.get(spec.relation_field),
                spec.id_key,
            ),
            new=current_resources,
        )

    def iter_needed_occupancy_nodes(self) -> dict[str, set[ResourceNode]]:
        """Return current timetable nodes consulted by the dependency algorithm."""
        nodes_by_graph = {spec.graph_name: set() for spec in RESOURCE_SPECS}

        for session_id, changes in self.changes.items():
            session_data = self.sessions_by_change_key.get(
                normalize_id(session_id),
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
                if not time.changed and not resources.changed:
                    continue

                for old_resource, _new_resource in resources.pairs(time.changed):
                    for old_time_slot in time.old.time_slots:
                        nodes_by_graph[spec.graph_name].add(
                            time.old.node(old_resource, old_time_slot),
                        )

        return nodes_by_graph

    def load_scoped_occupancy(
        self,
        session: DBSession,
    ) -> dict[str, ResourceOccupancy]:
        """Load current timetable occupancy only for dependency-relevant nodes."""
        nodes_by_graph = self.iter_needed_occupancy_nodes()
        occupancy_loader = ResourceOccupancyLoader(session)
        return {
            spec.graph_name: occupancy_loader.load(spec, nodes_by_graph[spec.graph_name])
            for spec in RESOURCE_SPECS
        }

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
                normalize_id(session_id),
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
        session_id: SessionId,
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
            normalize_id(session_id): session_id for session_id in self.changes
        }

        dependency_graph.add_nodes_from(self.changes.keys())

        for resource_graph in graphs.values():
            for old_node, _new_node, edge_data in resource_graph.edges(data=True):
                moving_sessions = edge_data.get("ids", [])
                final_slot_sessions = resource_graph.nodes[old_node].get("ids", [])

                for moving_session_id in moving_sessions:
                    moving_change_key = change_key_by_session_id.get(
                        normalize_id(moving_session_id),
                    )
                    if moving_change_key is None:
                        continue

                    for final_slot_session_id in final_slot_sessions:
                        final_slot_change_key = change_key_by_session_id.get(
                            normalize_id(final_slot_session_id),
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
    ) -> list[list[SessionId]]:
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
            self.sort_group_by_classes(
                cast(set[SessionId], condensed_graph.nodes[component]["members"]),
            )
            for component in self.topological_sort_by_classes(condensed_graph)
        ]

    def get_graph_ordered_modifications(self) -> list[tuple[SessionId, str]]:
        """Return changed sessions in graph order with their export step type."""
        if self.dependency_graph is None:
            self.build_graph()

        ordered_modifications: list[tuple[SessionId, str]] = []
        for dependency_group in self.order_change_groups_using_graph():
            step_type = "exchange" if self.is_exact_time_exchange(dependency_group) else "move"
            ordered_modifications.extend((session_id, step_type) for session_id in dependency_group)

        return ordered_modifications

    def is_exact_time_exchange(self, dependency_group: list[SessionId]) -> bool:
        """Return whether a dependency cycle is an exact time-slot exchange."""
        if len(dependency_group) < 2:
            return False

        old_placements = []
        new_placements = []

        for session_id in dependency_group:
            session_data = self.sessions_by_change_key.get(normalize_id(session_id))
            if session_data is None:
                return False

            movement = self.build_time_movement(session_data, self.changes[session_id])
            old_placements.append(self.time_placement_key(movement.old))
            new_placements.append(self.time_placement_key(movement.new))

        return sorted(old_placements) == sorted(new_placements)

    @staticmethod
    def time_placement_key(placement: TimePlacement) -> tuple[tuple[int, ...], str, str]:
        """Return a comparable key for one session's occupied time slots."""
        return (placement.time_slots, str(placement.weekday), str(placement.week))

    def build_modification_steps(
        self,
        ordered_modifications: list[tuple[SessionId, str]] | None = None,
    ) -> list[ExportGraphStep]:
        """Return export-ready modification steps with dependencies and session data."""
        use_graph = ordered_modifications is None
        if ordered_modifications is None:
            ordered_modifications = self.get_graph_ordered_modifications()

        dependencies = self.get_dependencies() if use_graph else self.get_empty_dependencies()
        change_key_by_session_id = {
            normalize_id(session_id): session_id for session_id in self.changes
        }
        grouped_steps: dict[tuple[str, str], ExportGraphStep] = {}

        for raw_session_id, step_type in ordered_modifications:
            session_id = change_key_by_session_id.get(normalize_id(raw_session_id))
            if session_id is None:
                continue

            key = self.get_session_group_key(session_id)
            step = grouped_steps.setdefault(
                key,
                {
                    "type": step_type,
                    "session_ids": [],
                },
            )
            if step_type == "exchange":
                step["type"] = "exchange"

            cast(list[SessionId], step["session_ids"]).append(session_id)

        return [
            cast(
                ExportGraphStep,
                ExportModificationStep.model_validate(
                    self.build_modification_step(
                        cast(list[SessionId], step["session_ids"]),
                        cast(str, step["type"]),
                        dependencies,
                    ),
                ).model_dump(mode="json"),
            )
            for step in grouped_steps.values()
        ]

    def get_empty_dependencies(self) -> DependencyMap:
        """Return an empty dependency mapping for table-ordered export steps."""
        return {session_id: [] for session_id in self.changes}

    def get_session_group_key(self, session_id: SessionId) -> tuple[str, str]:
        """Return the recurring-block key used to group export changes."""
        session_data = self.get_public_session_data(session_id)
        block_id = session_data.get("original_block_id", session_id)
        changes_key = str(jsonable(self.groupable_changes(self.changes[session_id])))
        return (normalize_id(block_id), changes_key)

    def build_modification_step(
        self,
        session_ids: list[SessionId],
        step_type: str,
        dependencies: DependencyMap,
    ) -> ExportGraphStep:
        """Build one export step from already grouped changed sessions."""
        return {
            "type": step_type,
            **self.build_session_group(session_ids, dependencies),
        }

    def build_session_group(
        self,
        session_ids: list[SessionId],
        dependencies: DependencyMap,
    ) -> ExportGraphStep:
        """Return one frontend-ready recurring-block modification group."""
        sorted_session_ids = self.sort_session_ids_by_week(session_ids)
        representative_id = sorted_session_ids[0]
        representative_session = self.get_public_session_data(representative_id)
        weeks = [
            self.get_public_session_data(session_id)["week"] for session_id in sorted_session_ids
        ]
        original_block_id = representative_session.get("original_block_id", representative_id)
        all_block_weeks = self.get_original_block_weeks(original_block_id)

        return {
            "original_block_id": original_block_id,
            "session_ids": [str(session_id) for session_id in sorted_session_ids],
            "weeks": weeks,
            "week_range": self.build_week_range(weeks),
            "applies_to_all_weeks": set(map(str, weeks)) == set(map(str, all_block_weeks)),
            "modifications": self.build_group_modifications(sorted_session_ids),
            "dependencies": sorted(
                {
                    dependency
                    for session_id in sorted_session_ids
                    for dependency in dependencies[session_id]
                    if dependency not in sorted_session_ids
                },
                key=str,
            ),
            "session": representative_session,
        }

    def get_original_block_weeks(self, original_block_id: GraphPrimitive) -> list[GraphPrimitive]:
        """Return every week represented by one recurring original block."""
        normalized_block_id = normalize_id(original_block_id)
        if (
            hasattr(self, "original_block_weeks")
            and normalized_block_id in self.original_block_weeks
        ):
            return self.original_block_weeks[normalized_block_id]

        weeks = [
            session_data["week"]
            for session_data in self.initial_sessions.values()
            if normalize_id(session_data.get("original_block_id", session_data["id"]))
            == normalized_block_id
        ]

        return weeks or [self.initial_sessions[normalized_block_id]["week"]]

    def sort_session_ids_by_week(self, session_ids: list[SessionId]) -> list[SessionId]:
        """Sort session ids by their public week and then by id."""
        return sorted(
            session_ids,
            key=lambda session_id: (
                self.get_public_session_data(session_id).get("week"),
                str(session_id),
            ),
        )

    def build_group_modifications(self, session_ids: list[SessionId]) -> SessionChanges:
        """Return modifications shared by a displayed recurring-block group."""
        if len(session_ids) <= 1:
            return self.changes[session_ids[0]]

        # The individual sessions in a recurring block necessarily differ by
        # week. The frontend displays that as a grouped week range, so keeping a
        # representative week row here would make the block look split again.
        return self.groupable_changes(self.changes[session_ids[0]])

    @staticmethod
    def groupable_changes(changes: SessionChanges) -> SessionChanges:
        """Return changes that can be compared/rendered across recurring weeks."""
        return {field: change for field, change in changes.items() if field != "week"}

    @staticmethod
    def build_week_range(weeks: list[GraphValue]) -> ExportGraphStep:
        """Return whether a sorted list of weeks can be displayed as a range."""
        unique_weeks = sorted(
            {
                parsed_week
                for week in weeks
                if (parsed_week := parse_week_date(cast(GraphPrimitive, week))) is not None
            },
        )
        if not unique_weeks:
            return {"start": None, "end": None, "contiguous": False}

        contiguous = all(
            current - previous == timedelta(days=7)
            for previous, current in itertools.pairwise(unique_weeks)
        )

        return {
            "start": unique_weeks[0].isoformat(),
            "end": unique_weeks[-1].isoformat(),
            "contiguous": contiguous,
        }

    def get_public_session_data(self, session_id: SessionId) -> SessionSnapshot:
        """Return session data without graph-only resource id fields."""
        session_data = dict(self.initial_sessions[normalize_id(session_id)])

        for field in ("room_ids", "teacher_ids", "class_ids"):
            session_data.pop(field, None)

        return cast(
            SessionSnapshot,
            ExportSessionSnapshot.model_validate(session_data).model_dump(mode="json"),
        )

    def get_session_classes(self, session_id: SessionId) -> tuple[str, ...]:
        """Return sorted class codes for a session id."""
        session_data = self.sessions_by_change_key.get(
            normalize_id(session_id),
            {},
        )
        return tuple(
            sorted(
                str(class_code)
                for class_code in cast(list[GraphPrimitive], session_data.get("classes", []))
            ),
        )

    def get_group_classes(self, group: set[SessionId] | list[SessionId]) -> tuple[str, ...]:
        """Return sorted class codes touched by a group of session ids."""
        classes: set[str] = set()

        for session_id in group:
            classes.update(self.get_session_classes(session_id))

        return tuple(sorted(classes))

    def sort_group_by_classes(self, group: set[SessionId]) -> list[SessionId]:
        """Sort sessions inside one dependency group by class, then by id."""
        return sorted(
            group,
            key=lambda session_id: (
                self.get_session_classes(session_id),
                str(session_id),
            ),
        )

    def topological_sort_by_classes(self, condensed_graph: nx.DiGraph) -> list[int]:
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
        group: set[SessionId],
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

    def build_graph(self) -> dict[str, nx.DiGraph]:
        """Build resource graphs and cache the resulting change dependency graph.

        Returns:
            A dictionary with room, teacher, and class resource graphs.
        """
        graphs = {spec.graph_name: nx.DiGraph() for spec in RESOURCE_SPECS}

        for graph_name, occupancy in self.scoped_occupancy.items():
            graph = graphs[graph_name]
            for node, session_ids in occupancy.items():
                graph.add_node(node, ids=list(session_ids))

        self.connect_nodes_according_to_changes(graphs)
        self.dependency_graph = self.build_change_dependency_graph(graphs)
        return graphs

    def get_dependencies(
        self,
        *,
        transitive: bool = False,
    ) -> DependencyMap:
        """Return prerequisite changes for each changed-session node.

        Args:
            transitive: If false, include only direct prerequisites. If true,
                include the full chain of prerequisites.
        """
        if self.dependency_graph is None:
            self.build_graph()

        assert self.dependency_graph is not None
        dependencies: DependencyMap = {}

        for node in self.dependency_graph.nodes:
            if transitive:
                node_dependencies = cast(set[SessionId], nx.ancestors(self.dependency_graph, node))
            else:
                node_dependencies = cast(
                    list[SessionId],
                    self.dependency_graph.predecessors(node),
                )

            dependencies[cast(SessionId, node)] = sorted(node_dependencies, key=str)

        return dependencies
