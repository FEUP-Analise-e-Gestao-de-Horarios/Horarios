"""Unit tests for :func:`src.ingestion.parsers.teacher_page.extract_teacher_info`.

The parser reads the three ``<br>``-separated text nodes of the ``cabtitulo``
cell (header, acronym, code) and derives the name from the header, whose
displayed sigla is not always the acronym. These tests pin each shape: plain,
apostrophe/punctuation, empty name, and siglas that differ from or extend the
acronym.
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


def test_apostrophe_in_name_is_stripped() -> None:
    """An apostrophe in the name is stripped along with other punctuation."""
    assert _info(first_node="ABC - O'Brien", acronym="ABC", code=99) == (
        "ABC",
        "OBrien",
        99,
    )


def test_empty_name_falls_back_to_acronym() -> None:
    """When no name text follows the acronym, the acronym is used as the name."""
    assert _info(first_node="ABC", acronym="ABC", code=5) == ("ABC", "ABC", 5)


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


# ---------------------------------------------------------------------------
# -- Name recovery when the header sigla is not the acronym (bugfix)
# ---------------------------------------------------------------------------


def test_name_recovered_when_sigla_differs_from_acronym() -> None:
    """The header's displayed sigla is not always the acronym.

    Here the header reads ``AJCA-Albertino …`` but the acronym node is ``AA``.
    The name must be recovered from the header instead of collapsing to the
    acronym. Real page: ``docente_AA_481933`` (see ``test_real_pages``).
    """
    assert _info(
        first_node="AJCA-Albertino José Castanho Arteiro",
        acronym="AA",
        code=481933,
    ) == ("AA", "Albertino José Castanho Arteiro", 481933)


def test_name_recovered_when_sigla_extends_acronym() -> None:
    """A header sigla that extends the acronym (``AMMTB`` vs ``AMM``) is peeled off."""
    assert _info(
        first_node="AMMTB - Ana Mafalda Matos",
        acronym="AMM",
        code=7,
    ) == ("AMM", "Ana Mafalda Matos", 7)


def test_name_parsed_when_acronym_contains_separator() -> None:
    """The acronym node may itself contain ``" - "`` (e.g. ``DCC - ACM``)."""
    assert _info(
        first_node="DCC - ACM - André Couto Meira",
        acronym="DCC - ACM",
        code=3,
    ) == ("DCC - ACM", "André Couto Meira", 3)


def test_name_recovered_when_sigla_extends_acronym_with_plain_dash() -> None:
    """The extends-sigla case must also work with a bare ``-`` separator.

    Same shape as ``test_name_recovered_when_sigla_extends_acronym`` but with the
    spaceless separator the real ``AJCA-…`` page uses. The residual sigla chars
    (``TB``) must still be peeled off instead of fusing into the name.
    """
    assert _info(
        first_node="AMMTB-Ana Mafalda Matos",
        acronym="AMM",
        code=7,
    ) == ("AMM", "Ana Mafalda Matos", 7)


def test_multipart_name_keeps_all_segments() -> None:
    """The name is split off at the *first* separator, so a name that itself
    contains ``" - "`` keeps every part (the inner ``-`` is then stripped as
    punctuation, leaving the surrounding spaces)."""
    assert _info(
        first_node="ABC - Ana - Sofia Costa",
        acronym="ABC",
        code=8,
    ) == ("ABC", "Ana  Sofia Costa", 8)
