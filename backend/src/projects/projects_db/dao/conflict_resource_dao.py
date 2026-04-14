from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.projects.projects_db.models.session import Session as SessionModel


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
    def _parse_grouped_session_ids(raw_session_ids: str | None) -> list[UUID]:
        if not raw_session_ids:
            return []

        session_ids: list[UUID] = []
        for raw_session_id in raw_session_ids.split(","):
            normalized = raw_session_id.strip()
            if not normalized:
                continue

            try:
                session_ids.append(UUID(normalized))
            except ValueError:
                session_ids.append(UUID(hex=normalized))

        return session_ids

    @staticmethod
    def _mapping_for_columns(
        row: object,
        columns: Sequence[ConflictResourceColumn],
    ) -> dict[str, object]:
        row_mapping = row._mapping
        return {column.alias: row_mapping[column.alias] for column in columns}

    def get_conflicting_slots(
        self,
        spec: ConflictResourceSpec,
    ) -> list[dict[str, object]]:
        """Return conflicting resource allocations grouped by exact session slot."""
        identity_columns = (spec.id_column, *spec.identifying_columns)

        stmt = select(
            *(column.column.label(column.alias) for column in identity_columns),
            SessionModel.week,
            SessionModel.weekday,
            SessionModel.start_time,
            SessionModel.duration,
            func.count(SessionModel.id).label("collisions"),
            func.group_concat(SessionModel.id, ",").label("session_ids"),
        ).select_from(spec.model)

        for join in spec.joins:
            stmt = stmt.join(join.target, join.onclause)

        stmt = (
            stmt.group_by(
                *(column.column for column in identity_columns),
                SessionModel.week,
                SessionModel.weekday,
                SessionModel.start_time,
                SessionModel.duration,
            )
            .having(func.count(SessionModel.id) > 1)
            .order_by(
                *(column.column for column in spec.identifying_columns),
                SessionModel.week,
                SessionModel.weekday,
                SessionModel.start_time,
                SessionModel.duration,
            )
        )

        rows = self.session.execute(stmt).all()

        return [
            {
                **self._mapping_for_columns(row, identity_columns),
                "week": row.week,
                "weekday": row.weekday,
                "start_time": row.start_time,
                "duration": row.duration,
                "collisions": row.collisions,
                "session_ids": self._parse_grouped_session_ids(row.session_ids),
            }
            for row in rows
        ]
