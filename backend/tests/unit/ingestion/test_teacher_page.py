"""Unit tests for :func:`src.ingestion.parsers.teacher_page.extract_teacher_info`.

The parser reverse-engineers acronym/name/code from the ``repr`` of the
``cabtitulo`` cell's child nodes, so it is sensitive to how the three
``<br/>``-separated text nodes are shaped. These tests pin the behaviour of
each formatting branch (plain, apostrophe, empty name, punctuation).
"""

import pytest
from bs4 import BeautifulSoup

from src.ingestion.parsers.teacher_page import extract_teacher_info
from tests.unit.ingestion import _html as H


def _info(**kwargs: object):
    return extract_teacher_info(H.soup(H.teacher_page(**kwargs)))


def test_plain_acronym_name_code() -> None:
    assert _info() == ("ABC", "Ada Berta Costa", 123)


def test_custom_values() -> None:
    assert _info(acronym="JMS", name="José Maria Silva", code=451) == (
        "JMS",
        "José Maria Silva",
        451,
    )


def test_apostrophe_in_name_uses_quote_branch() -> None:
    """A single quote in a text node forces ``repr`` to switch to double quotes,
    exercising the parser's ``'"' in content`` branch; punctuation is stripped."""
    assert _info(first_node="ABC - O'Brien", acronym="ABC", code=99) == (
        "ABC",
        "OBrien",
        99,
    )


def test_empty_name_falls_back_to_acronym() -> None:
    """When no name text follows the acronym, the acronym is used as the name."""
    assert _info(first_node="ABC", acronym="ABC", code=5) == ("ABC", "ABC", 5)


def test_name_dropped_when_first_node_prefix_differs_from_acronym() -> None:
    """KNOWN WART — minimal repro of the real ``teacher_name_is_acronym`` fixture.

    ``extract_teacher_info`` only recovers the name when the acronym occurs as a
    substring of the first node (``name = first[len(acronym):] if acronym in
    first else ""``). Here the acronym "AA" does not appear anywhere in
    "AJCA-Albertino José Castanho Arteiro", so the check fails, the name becomes
    empty and falls back to the acronym — the real name is dropped. Pinned as
    current behaviour (25 such pages exist in the captured corpus); see
    ``test_real_pages`` for the real page this reproduces.
    """
    assert _info(
        first_node="AJCA-Albertino José Castanho Arteiro",
        acronym="AA",
        code=481933,
    ) == ("AA", "AA", 481933)


def test_punctuation_is_stripped_from_name() -> None:
    assert _info(first_node="ABC - Zé, Jr.", acronym="ABC", code=9) == (
        "ABC",
        "Zé Jr",
        9,
    )


def test_missing_cabtitulo_raises() -> None:
    soup = BeautifulSoup("<html><body>no header here</body></html>", "html.parser")
    with pytest.raises(ValueError, match="cabtitulo"):
        extract_teacher_info(soup)
