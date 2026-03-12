import sqlite3
from datetime import date, timedelta


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


def check_date_range_overlap(range_1: tuple[date, date], range_2: tuple[date, date]) -> bool:
    """Check whether two date ranges overlap or are within one week of each other.

    Returns True if the two date ranges either overlap directly, or if any
    boundary of one range falls within one week of the opposing boundary of
    the other range. This looser-than-strict overlap check is useful for
    matching schedule entries that may span slightly different week boundaries.

    Args:
        range_1: (start, end) dates of the first range.
        range_2: (start, end) dates of the second range.

    Returns:
        True if the ranges overlap or are within one week of each other,
        False otherwise.
    """
    week_start_1, week_end_1 = range_1
    week_start_2, week_end_2 = range_2
    overlap = week_start_1 <= week_end_2 and week_end_1 >= week_start_2
    one_week_or_less1 = abs(week_end_1 - week_start_2) <= timedelta(weeks=1)
    one_week_or_less2 = abs(week_start_1 - week_end_2) <= timedelta(weeks=1)
    return overlap or one_week_or_less1 or one_week_or_less2
