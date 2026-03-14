import sqlite3

from src.ingestion.schemas.misc import Time, WeekDay
from src.ingestion.schemas.rooms import RoomLinks


def ingest_room(cursor: sqlite3.Cursor, room: RoomLinks) -> None:
    """Insert a room record into the ``salas`` table.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        room: Room data to persist, including name, type, size, and seat count.
    """
    cursor.execute(
        "INSERT INTO salas(numero, tipo, capacidade, tamanhoComp) VALUES (?, ?, ?, ?)",
        (room["name"], room["type_"], room["size"], room["seats"]),
    )


def ingest_room_red_blocks(
    cursor: sqlite3.Cursor,
    room_name: str,
    time: Time,
    day: WeekDay,
) -> None:
    """Link an unavailability block to a room in the ``salaBloco`` table.

    Looks up the ``blocosVermelhos`` row for the given time and day. If found,
    inserts a ``(block_id, room_name)`` pair into ``salaBloco``, ignoring
    duplicates. If no matching block exists, the call is silently skipped.

    Args:
        cursor: Active SQLite cursor used to execute the queries.
        room_name: Name of the room to associate with the block.
        time: Time slot encoded as ``HHMM`` (e.g. ``900`` for 09:00).
        day: Day of the week for the unavailability block.
    """
    result = cursor.execute(
        "SELECT id FROM blocosVermelhos WHERE hora=? AND diaSemana=?",
        (time, day),
    ).fetchone()

    if result:
        cursor.execute(
            "INSERT OR IGNORE INTO salaBloco (idBloco, idSala) VALUES (?, ?)",
            (result[0], room_name),
        )
