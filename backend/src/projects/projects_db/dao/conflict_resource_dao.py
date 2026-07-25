from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject


@dataclass(frozen=True)
class ConflictResourceColumn:
    """A selected resource column and the alias used in the conflict payload."""

    alias: str
    column: object


@dataclass(frozen=True)
class ConflictResourceJoin:
    """A join needed to reach sessions or enrich resource identification."""

    target: object
    onclause: object


@dataclass(frozen=True)
class ConflictResourceSpec:
    """Configuration for conflict detection on a resource linked to sessions."""

    model: object
    id_column: ConflictResourceColumn
    identifying_columns: Sequence[ConflictResourceColumn]
    joins: Sequence[ConflictResourceJoin]


class ConflictResourceDAO:
    """Shared conflict query for resources connected to scheduled sessions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _mapping_for_columns(
        row: object,
        columns: Sequence[ConflictResourceColumn],
    ) -> dict[str, object]:
        row_mapping = row._mapping
        return {column.alias: row_mapping[column.alias] for column in columns}

    @staticmethod
    def to_minutes(hhmm: int) -> int:
        return (hhmm // 100) * 60 + (hhmm % 100)

    @staticmethod
    def _duration_from_minutes(minutes: int) -> int:
        return minutes // 30

    def _cluster_overlaps(
        self,
        rows: Sequence[object],
        identity_columns: Sequence[ConflictResourceColumn],
    ) -> list[dict[str, object]]:
        buckets: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)

        for row in rows:
            row_mapping = row._mapping
            identity = {column.alias: row_mapping[column.alias] for column in identity_columns}
            bucket_key = (
                *(row_mapping[column.alias] for column in identity_columns),
                row.week,
                row.weekday,
            )
            start_min = self.to_minutes(row.start_time)
            end_min = start_min + int(row.duration) * 30

            buckets[bucket_key].append(
                {
                    "identity": identity,
                    "week": row.week,
                    "weekday": row.weekday,
                    "start_time": row.start_time,
                    "duration": row.duration,
                    "start_min": start_min,
                    "end_min": end_min,
                    "session_id": row.session_id,
                },
            )

        conflicts: list[dict[str, object]] = []

        for bucket_rows in buckets.values():
            sorted_rows = sorted(
                bucket_rows,
                key=lambda row: (
                    int(row["start_min"]),
                    int(row["end_min"]),
                    str(row["session_id"]),
                ),
            )

            current_cluster: dict[str, object] | None = None

            for row in sorted_rows:
                if current_cluster is None:
                    current_cluster = {
                        **row["identity"],
                        "week": row["week"],
                        "weekday": row["weekday"],
                        "start_time": row["start_time"],
                        "duration": row["duration"],
                        "start_min": row["start_min"],
                        "end_min": row["end_min"],
                        "session_ids": [row["session_id"]],
                    }
                    continue

                if int(row["start_min"]) < int(current_cluster["end_min"]):
                    current_cluster["end_min"] = max(
                        int(current_cluster["end_min"]),
                        int(row["end_min"]),
                    )
                    current_cluster["duration"] = self._duration_from_minutes(
                        int(current_cluster["end_min"]) - int(current_cluster["start_min"]),
                    )
                    current_cluster["session_ids"].append(row["session_id"])
                    continue

                if len(current_cluster["session_ids"]) > 1:
                    conflicts.append(
                        {
                            key: value
                            for key, value in current_cluster.items()
                            if key not in {"start_min", "end_min"}
                        },
                    )

                current_cluster = {
                    **row["identity"],
                    "week": row["week"],
                    "weekday": row["weekday"],
                    "start_time": row["start_time"],
                    "duration": row["duration"],
                    "start_min": row["start_min"],
                    "end_min": row["end_min"],
                    "session_ids": [row["session_id"]],
                }

            if current_cluster and len(current_cluster["session_ids"]) > 1:
                conflicts.append(
                    {
                        key: value
                        for key, value in current_cluster.items()
                        if key not in {"start_min", "end_min"}
                    },
                )

        return conflicts

    @staticmethod
    def _group_recurring_conflicts(
        conflicts: Sequence[dict[str, object]],
        identity_columns: Sequence[ConflictResourceColumn],
    ) -> list[dict[str, object]]:
        grouped: dict[tuple[object, ...], dict[str, object]] = {}

        for conflict in conflicts:
            key = (
                *(conflict[column.alias] for column in identity_columns),
                conflict["weekday"],
                conflict["start_time"],
                conflict["duration"],
            )
            existing = grouped.get(key)
            session_ids = list(cast("Sequence[object]", conflict["session_ids"]))

            if existing is None:
                grouped[key] = {
                    **conflict,
                    "weeks": [conflict["week"]],
                    "session_ids": session_ids,
                    "collisions": len(session_ids),
                }
                continue

            cast("list[object]", existing["weeks"]).append(conflict["week"])
            cast("list[object]", existing["session_ids"]).extend(session_ids)
            existing["collisions"] = max(int(existing["collisions"]), len(session_ids))

        result = []
        for conflict in grouped.values():
            weeks = sorted(set(cast("Sequence[object]", conflict["weeks"])), key=str)
            session_ids = sorted(
                set(cast("Sequence[object]", conflict["session_ids"])),
                key=str,
            )
            result.append(
                {
                    **conflict,
                    "week": weeks[0],
                    "weeks": weeks,
                    "session_ids": session_ids,
                },
            )

        return sorted(
            result,
            key=lambda conflict: (
                *(str(conflict[column.alias]) for column in identity_columns),
                conflict["week"],
                str(conflict["weekday"]),
                int(conflict["start_time"]),
                int(conflict["duration"]),
            ),
        )

    def _add_subject_labels(self, conflicts: list[dict[str, object]]) -> list[dict[str, object]]:
        session_ids = {
            session_id
            for conflict in conflicts
            for session_id in cast("Sequence[object]", conflict["session_ids"])
        }
        if not session_ids:
            return conflicts

        rows = self.session.execute(
            select(
                SessionClassSubject.session_id,
                SessionClassSubject.class_id,
                Subject.acronym,
                Subject.code,
            )
            .join(Subject, Subject.id == SessionClassSubject.subject_id)
            .where(SessionClassSubject.session_id.in_(session_ids)),
        ).all()
        labels_by_session: dict[object, list[tuple[object, str]]] = defaultdict(list)
        for row in rows:
            labels_by_session[row.session_id].append(
                (row.class_id, f"{row.acronym} ({row.code})"),
            )

        for conflict in conflicts:
            class_id = conflict.get("class_id")
            labels = {
                label
                for session_id in cast("Sequence[object]", conflict["session_ids"])
                for row_class_id, label in labels_by_session.get(session_id, [])
                if class_id is None or row_class_id == class_id
            }
            conflict["subject_labels"] = sorted(labels)

        return conflicts

    def get_conflicting_slots(
        self,
        spec: ConflictResourceSpec,
    ) -> list[dict[str, object]]:
        """Return overlapping resource allocations grouped into conflict windows."""
        identity_columns = (spec.id_column, *spec.identifying_columns)

        stmt = select(
            *(column.column.label(column.alias) for column in identity_columns),
            SessionModel.id.label("session_id"),
            SessionModel.week,
            SessionModel.weekday,
            SessionModel.start_time,
            SessionModel.duration,
        ).select_from(spec.model)

        for join in spec.joins:
            stmt = stmt.join(join.target, join.onclause)

        stmt = stmt.order_by(
            *(column.column for column in spec.identifying_columns),
            SessionModel.week,
            SessionModel.weekday,
            SessionModel.start_time,
            SessionModel.duration,
            SessionModel.id,
        )

        rows = self.session.execute(stmt).all()

        conflicts = self._cluster_overlaps(rows, identity_columns)
        return self._add_subject_labels(
            self._group_recurring_conflicts(conflicts, identity_columns),
        )
