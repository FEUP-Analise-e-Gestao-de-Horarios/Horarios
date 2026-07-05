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


def test_name_recovered_when_acronym_prefixes_a_multitoken_sigla() -> None:
    """When the acronym is only a *prefix* of a sigla that carries its own
    ``" - "`` (acronym ``DCC`` vs sigla ``DCC - ACM``), peeling the acronym
    leaves the residual sigla token before the name. The name is split off at
    the *last* ``" - "`` so that residual token is consumed rather than fused
    into the name."""
    assert _info(
        first_node="DCC - ACM - André Couto Meira",
        acronym="DCC",
        code=8,
    ) == ("DCC", "André Couto Meira", 8)


def test_name_recovered_when_sigla_runs_into_a_dashless_name() -> None:
    """When the sigla equals the acronym and the name follows with only a space
    (no ``-`` at all), the residual after peeling the acronym is the name.

    Real page: ``MJMS Maria João Martins dos Santos`` — without this the name
    collapses to the acronym.
    """
    assert _info(
        first_node="MJMS Maria João Martins dos Santos",
        acronym="MJMS",
        code=8,
    ) == ("MJMS", "Maria João Martins dos Santos", 8)


def test_dashless_name_with_an_internal_hyphen_is_not_split_on_it() -> None:
    """A hyphen inside a whitespace-separated name is not the sigla separator.

    Combines the dashless ``MJMS Maria João …`` shape with a hyphenated
    surname: the residual after peeling must survive whole rather than being
    split at the surname's hyphen. (``re.sub`` still strips the hyphen itself.)
    """
    assert _info(
        first_node="MJMS Maria João Sá-Carneiro",
        acronym="MJMS",
        code=8,
    ) == ("MJMS", "Maria João SáCarneiro", 8)
