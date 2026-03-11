import sqlite3


def pre_insert_red_blocks(
    cursor: sqlite3.Cursor,
    conn: sqlite3.Connection,
) -> None:
    """Pre-populate the blocosVermelhos table with all time slots for each weekday.

    Inserts a row for every combination of weekday (Monday-Saturday) and
    30-minute time slot between 08:00 and 22:30, using integer encoding
    (e.g. 800 = 08:00, 830 = 08:30, ..., 2230 = 22:30).

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statements.
        conn: SQLite connection used to commit after each day's inserts.
    """
    # Time slots from 08:00 to 22:00 in 30min steps
    time_slots = [hour + minutes for hour in range(800, 2201, 100) for minutes in [0, 30]]

    for day in ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]:
        for time_slop in time_slots:
            cursor.execute(
                "INSERT INTO blocosVermelhos (hora, diaSemana) VALUES (?, ?)",
                (time_slop, day),
            )
        conn.commit()
