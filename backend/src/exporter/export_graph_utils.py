from __future__ import annotations

from datetime import date
from uuid import UUID

from src.exporter.export_graph_types import GraphPrimitive, GraphValue, SessionId


def convert_to_minutes(time: int | str) -> int:
    """Convert an ``HHMM`` or ``HH:MM`` time value into minutes after midnight."""
    if isinstance(time, str) and ":" in time:
        hours, minutes = time.split(":", maxsplit=1)
        return int(hours) * 60 + int(minutes)

    time = int(time)
    return time // 100 * 60 + time % 100


def normalize_id(value: GraphPrimitive) -> str:
    """Return an id string without hyphens so UUID forms can be compared."""
    return str(value).replace("-", "")


def to_uuid(value: SessionId) -> UUID:
    """Return an id value as a UUID accepted by SQLAlchemy UUID columns."""
    if isinstance(value, UUID):
        return value
    return UUID(hex=normalize_id(value))


def get_time_slots(start_time: int | str, duration: int) -> tuple[int, ...]:
    """Return every 30-minute slot occupied by a session."""
    start_time = convert_to_minutes(start_time)
    return tuple(start_time + i * 30 for i in range(int(duration)))


def parse_week_date(value: GraphPrimitive) -> date | None:
    """Parse a week value produced either before or after JSON serialization."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def jsonable(value: GraphValue) -> GraphValue:
    """Convert nested values to stable JSON-like values for comparisons."""
    if isinstance(value, dict):
        return {
            str(key): jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
