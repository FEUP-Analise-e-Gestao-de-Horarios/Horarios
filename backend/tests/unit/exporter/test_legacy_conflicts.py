"""Unit tests for :mod:`src.exporter.legacy.conflicts`.

The legacy conflict helpers detect resource overlaps over both ORM ``Session``
objects and serialized session mappings. Tests use light duck-typed stand-ins
(``SimpleNamespace``) for the ORM objects so they stay pure — no database.
"""

import datetime
from types import SimpleNamespace

from pytest import mark

from src.exporter.legacy.conflicts import (
    _class_ids,
    _normalize_scalar,
    _room_ids,
    _teacher_ids,
    _time_to_minutes,
    class_conflicts,
    room_conflicts,
    serialize_conflicts,
    sessions_conflict,
    sessions_overlap,
    teacher_conflicts,
)
from src.projects.projects_db.schemas.weekday import WeekDay

WEEK = datetime.date(2026, 1, 5)
OTHER_WEEK = datetime.date(2026, 1, 12)


def orm_session(
    session_id: str,
    *,
    start_time: int,
    duration: int = 2,
    week: datetime.date = WEEK,
    weekday: WeekDay = WeekDay.MONDAY,
    rooms: tuple[str, ...] = (),
    teachers: tuple[str, ...] = (),
    classes: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        id=session_id,
        week=week,
        weekday=weekday,
        start_time=start_time,
        duration=duration,
        rooms=[SimpleNamespace(id=room) for room in rooms],
        teachers=[SimpleNamespace(id=teacher) for teacher in teachers],
        session_class_subjects=[SimpleNamespace(class_id=class_id) for class_id in classes],
    )


def dict_session(
    *,
    start_time: int,
    duration: int = 2,
    week: str = "2026-01-05",
    weekday: str = "monday",
    room_ids: tuple[str, ...] = (),
    teacher_ids: tuple[str, ...] = (),
    class_subjects: object = None,
) -> dict:
    return {
        "week": week,
        "weekday": weekday,
        "start_time": start_time,
        "duration": duration,
        "room_ids": list(room_ids),
        "teacher_ids": list(teacher_ids),
        "class_subjects": {} if class_subjects is None else class_subjects,
    }


# ---------------------------------------------------------------------------
# -- _time_to_minutes
# ---------------------------------------------------------------------------


@mark.parametrize(
    ("hhmm", "expected"),
    [(0, 0), (830, 510), (1000, 600), (2359, 23 * 60 + 59)],
)
def test_time_to_minutes(hhmm: int, expected: int) -> None:
    assert _time_to_minutes(hhmm) == expected


# ---------------------------------------------------------------------------
# -- sessions_overlap (ORM objects)
# ---------------------------------------------------------------------------


def test_sessions_overlap_true_for_overlapping_window() -> None:
    a = orm_session("a", start_time=830)  # 510..570
    b = orm_session("b", start_time=900)  # 540..600
    assert sessions_overlap(a, b) is True


def test_sessions_overlap_false_for_adjacent_windows() -> None:
    a = orm_session("a", start_time=800, duration=2)  # 480..540
    b = orm_session("b", start_time=900, duration=2)  # 540..600
    # Touching but not overlapping (end == start).
    assert sessions_overlap(a, b) is False


def test_sessions_overlap_false_for_different_week() -> None:
    a = orm_session("a", start_time=830, week=WEEK)
    b = orm_session("b", start_time=830, week=OTHER_WEEK)
    assert sessions_overlap(a, b) is False


def test_sessions_overlap_false_for_different_weekday() -> None:
    a = orm_session("a", start_time=830, weekday=WeekDay.MONDAY)
    b = orm_session("b", start_time=830, weekday=WeekDay.TUESDAY)
    assert sessions_overlap(a, b) is False


# ---------------------------------------------------------------------------
# -- room / teacher / class conflicts (ORM lists)
# ---------------------------------------------------------------------------


def test_room_conflicts_pairs_overlapping_sessions_sharing_a_room() -> None:
    a = orm_session("a", start_time=830, rooms=("R1",))
    b = orm_session("b", start_time=900, rooms=("R1",))
    c = orm_session("c", start_time=830, rooms=("R2",))  # different room

    assert room_conflicts([a, b, c]) == {("a", "b")}


def test_room_conflicts_ignores_non_overlapping_sessions() -> None:
    a = orm_session("a", start_time=800, rooms=("R1",))
    b = orm_session("b", start_time=900, rooms=("R1",))  # adjacent, no overlap
    assert room_conflicts([a, b]) == set()


def test_teacher_conflicts_detects_shared_teacher_overlap() -> None:
    a = orm_session("a", start_time=830, teachers=("T1",))
    b = orm_session("b", start_time=845, teachers=("T1",))
    assert teacher_conflicts([a, b]) == {("a", "b")}


def test_class_conflicts_detects_shared_class_overlap() -> None:
    a = orm_session("a", start_time=830, classes=("C1",))
    b = orm_session("b", start_time=845, classes=("C1",))
    assert class_conflicts([a, b]) == {("a", "b")}


def test_conflicts_pair_ids_are_sorted_by_string() -> None:
    a = orm_session("zeta", start_time=830, rooms=("R1",))
    b = orm_session("alpha", start_time=845, rooms=("R1",))
    assert room_conflicts([a, b]) == {("alpha", "zeta")}


# ---------------------------------------------------------------------------
# -- serialize_conflicts
# ---------------------------------------------------------------------------


def test_serialize_conflicts_produces_session_pairs() -> None:
    serialized = serialize_conflicts({("a", "b")})
    assert serialized == [{"session1": "a", "session2": "b"}]


def test_serialize_conflicts_empty() -> None:
    assert serialize_conflicts(set()) == []


# ---------------------------------------------------------------------------
# -- sessions_conflict (ORM and mapping)
# ---------------------------------------------------------------------------


def test_sessions_conflict_true_for_shared_room_overlap_orm() -> None:
    a = orm_session("a", start_time=830, rooms=("R1",))
    b = orm_session("b", start_time=845, rooms=("R1", "R2"))
    assert sessions_conflict(a, b) is True


def test_sessions_conflict_false_when_no_shared_resource() -> None:
    a = orm_session("a", start_time=830, rooms=("R1",), teachers=("T1",))
    b = orm_session("b", start_time=845, rooms=("R2",), teachers=("T2",))
    assert sessions_conflict(a, b) is False


def test_sessions_conflict_false_when_not_overlapping_in_time() -> None:
    a = orm_session("a", start_time=800, rooms=("R1",))
    b = orm_session("b", start_time=900, rooms=("R1",))
    assert sessions_conflict(a, b) is False


def test_sessions_conflict_mapping_shares_class() -> None:
    a = dict_session(start_time=830, class_subjects={"C1": "S1"})
    b = dict_session(start_time=845, class_subjects={"C1": "S2"})
    assert sessions_conflict(a, b) is True


def test_sessions_conflict_mapping_no_shared_resource() -> None:
    a = dict_session(start_time=830, room_ids=("R1",))
    b = dict_session(start_time=845, room_ids=("R2",))
    assert sessions_conflict(a, b) is False


def test_sessions_conflict_mixed_orm_and_mapping() -> None:
    orm = orm_session("a", start_time=830, teachers=("T1",))
    mapping = dict_session(start_time=845, teacher_ids=("T1",))
    assert sessions_conflict(orm, mapping) is True


# ---------------------------------------------------------------------------
# -- id extraction helpers
# ---------------------------------------------------------------------------


def test_room_and_teacher_ids_from_mapping_and_orm() -> None:
    mapping = dict_session(start_time=830, room_ids=("R1",), teacher_ids=("T1", "T2"))
    assert _room_ids(mapping) == {"R1"}
    assert _teacher_ids(mapping) == {"T1", "T2"}

    orm = orm_session("a", start_time=830, rooms=("R1",), teachers=("T1",))
    assert _room_ids(orm) == {"R1"}
    assert _teacher_ids(orm) == {"T1"}


def test_class_ids_from_mapping_dict_uses_keys() -> None:
    mapping = dict_session(start_time=830, class_subjects={"C1": "S1", "C2": "S2"})
    assert _class_ids(mapping) == {"C1", "C2"}


def test_class_ids_from_mapping_sequence() -> None:
    mapping = dict_session(start_time=830, class_subjects=["C1", "C2"])
    assert _class_ids(mapping) == {"C1", "C2"}


def test_class_ids_from_orm() -> None:
    orm = orm_session("a", start_time=830, classes=("C1", "C2"))
    assert _class_ids(orm) == {"C1", "C2"}


# ---------------------------------------------------------------------------
# -- _normalize_scalar
# ---------------------------------------------------------------------------


def test_normalize_scalar_date_uses_isoformat() -> None:
    assert _normalize_scalar(datetime.date(2026, 1, 5)) == "2026-01-05"


def test_normalize_scalar_enum_uses_value() -> None:
    assert _normalize_scalar(WeekDay.MONDAY) == "monday"


def test_normalize_scalar_plain_scalar() -> None:
    assert _normalize_scalar(830) == "830"
    assert _normalize_scalar("monday") == "monday"
