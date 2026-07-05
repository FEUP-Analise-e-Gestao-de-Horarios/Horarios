"""Unit tests for :mod:`src.exporter.compact_payload`.

The compact payload is the wire/cache form: repeated room/teacher/class/subject
and session data is hoisted into ``entities`` maps and conflicts collapse to
tuples. The contract is that compaction is *lossless* — expanding a compacted
payload must reproduce the legacy expanded payload exactly — plus a set of
backward-compatible input shapes the expander must still accept (legacy
9-tuple conflicts, dict-style conflicts, string/tuple relation records).
"""

from copy import deepcopy

from pytest import mark, raises

from src.exporter.compact_payload import (
    compact_conflict,
    compact_conflict_kind,
    compact_export_payload,
    expand_compact_export_payload,
    expand_conflict,
    expand_modifications,
    find_entity,
    normalize_compact_id,
)
from src.exporter.schemas import ProjectExportPayload

# ---------------------------------------------------------------------------
# -- Payload builders
# ---------------------------------------------------------------------------


def _session_snapshot(session_id: str = "session-1") -> dict:
    return {
        "id": session_id,
        "original_block_id": "block-1",
        "start_time": 830,
        "duration": 2,
        "weekday": "monday",
        "week": "2026-01-05",
        "rooms": ["B101"],
        "teachers": [{"number": 1, "name": "Ada", "acronym": "AA"}],
        "classes": ["1LEIC01"],
        "subjects": [{"name": "IA", "acronym": "IA", "code": "IA001"}],
    }


def _full_payload() -> dict:
    return {
        "added_removed_sessions": {
            "added": [{"id": "added-1"}],
            "removed": [{"id": "removed-1"}],
        },
        "rooms_conflicts": [
            {
                "room_id": "room-1",
                "room_name": "B101",
                "week": "2026-01-05",
                "weeks": ["2026-01-05"],
                "weekday": "monday",
                "start_time": 830,
                "duration": 2,
                "collisions": 2,
                "session_ids": ["session-1", "session-2"],
                "subject_labels": ["IA (IA001)"],
            },
        ],
        "teacher_conflicts": [
            {
                "teacher_id": "teacher-1",
                "teacher_number": 7,
                "teacher_acronym": "AB",
                "teacher_name": "Ada Berta",
                "week": "2026-01-05",
                "weeks": ["2026-01-05"],
                "weekday": "monday",
                "start_time": 830,
                "duration": 2,
                "collisions": 2,
                "session_ids": ["session-1", "session-3"],
                "subject_labels": [],
            },
        ],
        "classes_conflicts": [
            # A different class than the one touched by the modification step
            # below, so no entity map collision hides class_shift (see
            # test_class_shift_is_dropped_when_class_also_appears_in_a_conflict).
            {
                "class_id": "class-2",
                "class_code": "1LEIC02",
                "week": "2026-01-05",
                "weeks": ["2026-01-05"],
                "weekday": "monday",
                "start_time": 830,
                "duration": 2,
                "collisions": 2,
                "session_ids": ["session-1", "session-4"],
                "subject_labels": ["IA (IA001)"],
            },
        ],
        "modification_steps": [
            {
                "type": "move",
                "original_block_id": "block-1",
                "session_ids": ["session-1"],
                "weeks": ["2026-01-05"],
                "week_range": {
                    "start": "2026-01-05",
                    "end": "2026-01-05",
                    "contiguous": True,
                },
                "applies_to_all_weeks": False,
                "modifications": {
                    "start_time": {"old": 830, "new": 1000},
                    "rooms": {
                        "added": [{"room_id": "room-9", "room_name": "B209"}],
                        "removed": [{"room_id": "room-1", "room_name": "B101"}],
                    },
                    "teachers": {
                        "added": [
                            {
                                "teacher_id": "teacher-9",
                                "teacher_number": 9,
                                "teacher_acronym": "ZZ",
                                "teacher_name": "Zeta",
                            },
                        ],
                        "removed": [],
                    },
                    "class_subjects": {
                        "added": [
                            {
                                "class_id": "class-1",
                                "class_code": "1LEIC01",
                                "class_shift": 1,
                                "subject_id": "subject-1",
                                "subject_number": 3,
                                "subject_code": "IA001",
                                "subject_acronym": "IA",
                                "subject_name": "Inteligencia Artificial",
                            },
                        ],
                        "removed": [],
                    },
                },
                "dependencies": [],
                "session": _session_snapshot(),
            },
        ],
    }


# ---------------------------------------------------------------------------
# -- normalize_compact_id / find_entity
# ---------------------------------------------------------------------------


def test_normalize_compact_id_strips_hyphens() -> None:
    assert normalize_compact_id("aa-bb-cc") == "aabbcc"
    assert normalize_compact_id(123) == "123"


def test_find_entity_exact_match_returns_copy() -> None:
    entities = {"rooms": {"r1": {"room_name": "B101"}}}
    result = find_entity(entities, "rooms", "r1")
    assert result == {"room_name": "B101"}
    result["room_name"] = "MUTATED"
    assert entities["rooms"]["r1"]["room_name"] == "B101"


def test_find_entity_normalized_lookup() -> None:
    entities = {"rooms": {"aabb": {"room_name": "B101"}}}
    assert find_entity(entities, "rooms", "aa-bb") == {"room_name": "B101"}


def test_find_entity_scan_fallback_when_stored_key_is_hyphenated() -> None:
    entities = {"rooms": {"aa-bb": {"room_name": "B101"}}}
    assert find_entity(entities, "rooms", "aabb") == {"room_name": "B101"}


def test_find_entity_missing_returns_empty_dict() -> None:
    assert find_entity({"rooms": {}}, "rooms", "nope") == {}
    assert find_entity({}, "teachers", "nope") == {}


# ---------------------------------------------------------------------------
# -- Lossless round-trip
# ---------------------------------------------------------------------------


def test_compact_then_expand_reproduces_expanded_payload() -> None:
    payload = _full_payload()

    compact = compact_export_payload(payload)
    expanded = expand_compact_export_payload(compact)

    expected = ProjectExportPayload.model_validate(payload).model_dump(mode="json")
    assert expanded.model_dump(mode="json") == expected


def test_compact_payload_hoists_repeated_entities() -> None:
    compact = compact_export_payload(_full_payload()).model_dump(mode="json")

    entities = compact["entities"]
    assert entities["rooms"]["room-1"] == {"room_name": "B101"}
    assert entities["teachers"]["teacher-1"]["teacher_name"] == "Ada Berta"
    # class-1 comes from the modification's class_subjects (full detail),
    # class-2 from the class conflict (code only).
    assert entities["classes"]["class-1"]["class_code"] == "1LEIC01"
    assert entities["classes"]["class-2"]["class_code"] == "1LEIC02"
    # The step session is stored once in the sessions entity map.
    assert "session-1" in entities["sessions"]


def test_compact_conflicts_are_tuple_encoded_with_kind_first() -> None:
    compact = compact_export_payload(_full_payload()).model_dump(mode="json")

    kinds = [conflict[0] for conflict in compact["conflicts"]]
    assert kinds == ["room", "teacher", "class"]
    room_conflict = compact["conflicts"][0]
    # (kind, resource_id, week, weeks, weekday, start, duration, collisions, sessions, labels)
    assert room_conflict[1] == "room-1"
    assert room_conflict[9] == ["IA (IA001)"]


def test_compact_step_replaces_session_with_reference() -> None:
    compact = compact_export_payload(_full_payload()).model_dump(mode="json")
    step = compact["modification_steps"][0]
    assert "session" not in step
    # Relation modifications collapse to id references.
    assert step["modifications"]["rooms"] == {"added": ["room-9"], "removed": ["room-1"]}
    assert step["modifications"]["class_subjects"]["added"] == [["class-1", "subject-1"]]


def test_empty_payload_round_trips() -> None:
    payload = {"added_removed_sessions": {"added": [], "removed": []}}
    compact = compact_export_payload(payload)
    expanded = expand_compact_export_payload(compact)
    assert expanded.model_dump(mode="json") == (
        ProjectExportPayload.model_validate(payload).model_dump(mode="json")
    )


# ---------------------------------------------------------------------------
# -- Backward-compatible expander inputs
# ---------------------------------------------------------------------------


def test_expand_conflict_accepts_legacy_9_tuple_without_subject_labels() -> None:
    entities = {"rooms": {"room-1": {"room_name": "B101"}}}
    legacy = (
        "room",
        "room-1",
        "2026-01-05",
        ["2026-01-05"],
        "monday",
        830,
        2,
        2,
        ["session-1", "session-2"],
    )
    expanded = expand_conflict(legacy, entities)
    assert expanded["room_id"] == "room-1"
    assert expanded["room_name"] == "B101"
    assert expanded["subject_labels"] == []


def test_expand_conflict_accepts_dict_style_conflict() -> None:
    entities = {"teachers": {"teacher-1": {"teacher_name": "Ada"}}}
    conflict = {
        "kind": "teacher",
        "resource_id": "teacher-1",
        "week": "2026-01-05",
        "weekday": "monday",
        "start_time": 830,
        "duration": 2,
        "collisions": 2,
        "session_ids": ["s1", "s2"],
        "subject_labels": [],
    }
    expanded = expand_conflict(conflict, entities)
    assert expanded["teacher_id"] == "teacher-1"
    assert expanded["teacher_name"] == "Ada"
    assert "kind" not in expanded
    assert "resource_id" not in expanded


def test_expand_modifications_accepts_string_and_tuple_relation_records() -> None:
    entities = {
        "rooms": {"room-9": {"room_name": "B209"}},
        "classes": {"class-1": {"class_code": "1LEIC01", "class_shift": 1}},
        "subjects": {"subject-1": {"subject_acronym": "IA"}},
    }
    modifications = {
        "rooms": {"added": ["room-9"], "removed": []},
        "class_subjects": {"added": [["class-1", "subject-1"]], "removed": []},
    }
    expanded = expand_modifications(modifications, entities)
    assert expanded["rooms"]["added"] == [{"room_id": "room-9", "room_name": "B209"}]
    class_subject = expanded["class_subjects"]["added"][0]
    assert class_subject["class_id"] == "class-1"
    assert class_subject["class_code"] == "1LEIC01"
    assert class_subject["subject_id"] == "subject-1"
    assert class_subject["subject_acronym"] == "IA"


def test_expand_modifications_skips_none_valued_fields() -> None:
    expanded = expand_modifications({"rooms": None, "start_time": {"old": 8, "new": 10}}, {})
    assert "rooms" not in expanded
    assert expanded["start_time"] == {"old": 8, "new": 10}


# ---------------------------------------------------------------------------
# -- compact_conflict_kind
# ---------------------------------------------------------------------------


@mark.parametrize(
    ("conflict", "expected"),
    [
        (("room", "r1"), "room"),
        (["class", "c1"], "class"),
        ({"kind": "teacher"}, "teacher"),
        ({}, None),
        ((), None),
        (123, None),
    ],
)
def test_compact_conflict_kind(conflict: object, expected: str | None) -> None:
    assert compact_conflict_kind(conflict) == expected  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# -- Error paths
# ---------------------------------------------------------------------------


def test_compact_conflict_rejects_unknown_kind() -> None:
    conflict = {
        "week": "2026-01-05",
        "weekday": "monday",
        "start_time": 830,
        "duration": 2,
        "collisions": 2,
        "session_ids": [],
    }
    with raises(ValueError, match="Unknown compact conflict kind"):
        compact_conflict("nonsense", conflict, {"rooms": {}, "teachers": {}, "classes": {}})  # type: ignore[arg-type]


def test_expand_conflict_rejects_unknown_tuple_kind() -> None:
    unknown = ("nonsense", "id", "w", None, "monday", 830, 2, 2, [], [])
    with raises(ValueError, match="Unknown compact conflict kind"):
        expand_conflict(unknown, {})


# ---------------------------------------------------------------------------
# -- Isolation / independence
# ---------------------------------------------------------------------------


def test_compaction_does_not_mutate_input_payload() -> None:
    payload = _full_payload()
    snapshot = deepcopy(payload)
    compact_export_payload(payload)
    assert payload == snapshot


# ---------------------------------------------------------------------------
# -- Characterization: entity-map collision between a conflict and a step
# ---------------------------------------------------------------------------


def test_class_shift_is_dropped_when_class_also_appears_in_a_conflict() -> None:
    # A class conflict populates entities["classes"][id] with only class_code
    # (conflicts don't carry shift). Because the class_subjects compactor uses
    # setdefault, a later modification referencing the *same* class id cannot
    # add class_shift, so it is lost across a round-trip. This documents the
    # current behavior; a fix should make this round-trip preserve class_shift.
    payload = {
        "added_removed_sessions": {"added": [], "removed": []},
        "classes_conflicts": [
            {
                "class_id": "class-1",
                "class_code": "1LEIC01",
                "week": "2026-01-05",
                "weekday": "monday",
                "start_time": 830,
                "duration": 2,
                "collisions": 2,
                "session_ids": ["session-1", "session-2"],
                "subject_labels": [],
            },
        ],
        "modification_steps": [
            {
                "type": "move",
                "original_block_id": "block-1",
                "session_ids": ["session-1"],
                "weeks": ["2026-01-05"],
                "week_range": {"start": "2026-01-05", "end": "2026-01-05", "contiguous": True},
                "modifications": {
                    "class_subjects": {
                        "added": [
                            {
                                "class_id": "class-1",
                                "class_code": "1LEIC01",
                                "class_shift": 1,
                                "subject_id": "subject-1",
                                "subject_acronym": "IA",
                                "subject_code": "IA001",
                                "subject_name": "IA",
                                "subject_number": 3,
                            },
                        ],
                        "removed": [],
                    },
                },
                "dependencies": [],
                "session": _session_snapshot(),
            },
        ],
    }

    expanded = expand_compact_export_payload(compact_export_payload(payload))
    added = expanded.model_dump(mode="json")["modification_steps"][0]["modifications"][
        "class_subjects"
    ]["added"][0]

    assert added["class_code"] == "1LEIC01"
    # class_shift is dropped by the collision (would be 1 without the conflict).
    assert added["class_shift"] is None
