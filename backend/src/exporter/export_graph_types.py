from dataclasses import dataclass
from datetime import date
from uuid import UUID

from src.projects.projects_db.schemas.weekday import WeekDay

type Resource = str | int
type ResourceNode = tuple[Resource, int, str, str]
type SessionId = str | UUID
type GraphPrimitive = str | int | float | bool | None | date | UUID
type GraphValue = GraphPrimitive | tuple[GraphValue, ...] | list[GraphValue] | dict[str, GraphValue]
type SessionSnapshot = dict[str, GraphValue]
type ChangeBucket = dict[str, GraphValue]
type SessionChanges = dict[str, GraphValue]
type DependencyMap = dict[SessionId, list[SessionId]]
type OrderedModification = tuple[SessionId, str]
type ResourceOccupancy = dict[ResourceNode, list[SessionId]]
type ExportGraphStep = dict[str, GraphValue]


@dataclass(frozen=True)
class TimePlacement:
    """A session placement in time, independent from rooms/teachers/classes."""

    time_slots: tuple[int, ...]
    weekday: WeekDay | str
    week: date | str

    def node(self, resource: Resource, time_slot: int) -> ResourceNode:
        """Return the graph node for this placement and one resource slot."""
        return (resource, time_slot, str(self.weekday), str(self.week))


@dataclass(frozen=True)
class TimeMovement:
    """Old and new time placement for a changed session."""

    old: TimePlacement
    new: TimePlacement
    changed: bool


@dataclass(frozen=True)
class ResourceMovement:
    """Old and new resources for one resource graph."""

    old: tuple[Resource, ...]
    new: tuple[Resource, ...]

    @property
    def changed(self) -> bool:
        """Whether the old and new resource sets differ."""
        return set(self.old) != set(self.new)

    def pairs(self, include_shared: bool) -> list[tuple[Resource, Resource]]:
        """Pair old and new resources that should receive movement edges."""
        old_unique = sorted(set(self.old), key=str)
        new_unique = sorted(set(self.new), key=str)
        old_set = set(old_unique)
        new_set = set(new_unique)

        if not old_unique or not new_unique:
            return []

        if old_set == new_set:
            return [(resource, resource) for resource in old_unique]

        shared = [resource for resource in old_unique if resource in new_set]
        removed = [resource for resource in old_unique if resource not in new_set]
        added = [resource for resource in new_unique if resource not in old_set]
        pairs: list[tuple[Resource, Resource]] = []

        if include_shared:
            pairs.extend((resource, resource) for resource in shared)

        if removed and added:
            pairs.extend(
                (old_resource, new_resource) for old_resource in removed for new_resource in added
            )
        elif added:
            pairs.extend(
                (old_resource, new_resource) for old_resource in shared for new_resource in added
            )
        elif removed:
            pairs.extend(
                (old_resource, new_resource) for old_resource in removed for new_resource in shared
            )

        if not pairs:
            pairs.extend(
                (old_resource, new_resource)
                for old_resource in old_unique
                for new_resource in new_unique
            )

        return pairs


@dataclass(frozen=True)
class ResourceSpec:
    """Configuration for one resource graph."""

    graph_name: str
    session_field: str
    relation_field: str
    id_key: str


RESOURCE_SPECS = (
    ResourceSpec("rooms", "room_ids", "rooms", "room_id"),
    ResourceSpec("teachers", "teacher_ids", "teachers", "teacher_id"),
    ResourceSpec("classes", "class_ids", "class_subjects", "class_id"),
)
