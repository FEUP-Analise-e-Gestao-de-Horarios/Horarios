"""Unit tests for ``ProjectExportView.format_export_payload``.

The response formatter accepts either a compact or an expanded payload (as a
pydantic model *or* a plain mapping) and renders it in the requested format.
This is pure — no request, no database — so it is unit-tested directly across
the model/mapping x compact/expanded matrix.
"""

from src.exporter.compact_payload import compact_export_payload
from src.exporter.schemas import ProjectExportPayload
from src.projects.views.export import ProjectExportView

_STEP = {
    "type": "move",
    "original_block_id": "block-1",
    "session_ids": ["session-1"],
    "weeks": ["2026-01-05"],
    "week_range": {"start": "2026-01-05", "end": "2026-01-05", "contiguous": True},
    "modifications": {"start_time": {"old": 830, "new": 1000}},
    "dependencies": [],
    "session": {
        "id": "session-1",
        "start_time": 830,
        "duration": 2,
        "weekday": "monday",
        "week": "2026-01-05",
        "rooms": ["B101"],
        "classes": ["1LEIC01"],
    },
}


def _expanded_model() -> ProjectExportPayload:
    return ProjectExportPayload.model_validate(
        {
            "added_removed_sessions": {"added": [], "removed": []},
            "modification_steps": [_STEP],
        },
    )


def _format(data, payload_format):
    return ProjectExportView.format_export_payload(data, payload_format)


# ---------------------------------------------------------------------------
# -- Compact source
# ---------------------------------------------------------------------------


def test_compact_model_to_compact() -> None:
    compact = compact_export_payload(_expanded_model())
    result = _format(compact, "compact")
    assert result["format"] == "compact_export_v1"
    assert "entities" in result


def test_compact_model_to_expanded() -> None:
    compact = compact_export_payload(_expanded_model())
    result = _format(compact, "expanded")
    assert "format" not in result
    assert result["modification_steps"][0]["session"]["id"] == "session-1"


def test_compact_mapping_to_expanded() -> None:
    compact_dict = compact_export_payload(_expanded_model()).model_dump(mode="json")
    result = _format(compact_dict, "expanded")
    assert "format" not in result
    assert result["modification_steps"][0]["type"] == "move"


# ---------------------------------------------------------------------------
# -- Expanded source
# ---------------------------------------------------------------------------


def test_expanded_model_to_compact() -> None:
    result = _format(_expanded_model(), "compact")
    assert result["format"] == "compact_export_v1"


def test_expanded_model_to_expanded() -> None:
    result = _format(_expanded_model(), "expanded")
    assert "format" not in result
    assert result["modification_steps"][0]["modifications"]["start_time"] == {
        "old": 830,
        "new": 1000,
    }


def test_expanded_mapping_to_compact() -> None:
    expanded_dict = _expanded_model().model_dump(mode="json")
    result = _format(expanded_dict, "compact")
    assert result["format"] == "compact_export_v1"


def test_expanded_mapping_to_expanded_round_trips() -> None:
    expanded_dict = _expanded_model().model_dump(mode="json")
    result = _format(expanded_dict, "expanded")
    assert result == expanded_dict
