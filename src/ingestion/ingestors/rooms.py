import sqlite3

from src.ingestion.schemas.misc import Time, WeekDay
from src.ingestion.schemas.rooms import RoomLinks


def ingest_room(cursor: sqlite3.Cursor, room: RoomLinks) -> None:
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
    result = cursor.execute(
        "SELECT id FROM blocosVermelhos WHERE hora=? AND diaSemana=?",
        (time, day),
    ).fetchone()

    if result:
        cursor.execute(
            "INSERT OR IGNORE INTO salaBloco (idBloco, idSala) VALUES (?, ?)",
            (result[0], room_name),
        )
