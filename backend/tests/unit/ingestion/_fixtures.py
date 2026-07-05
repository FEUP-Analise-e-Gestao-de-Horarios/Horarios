"""Loader for the checked-in **real** FEUP pages, used by the ingestion parser tests.

Where :mod:`_html` assembles the *minimum* synthetic markup each parser needs,
this module loads **byte-for-byte real pages** captured from a SIGARRA site
mirror. They exist to close the one gap synthetic fixtures cannot: the synthetic
builders encode the same structural assumptions as the parsers, so they can only
prove the parsers are self-consistent — not that they match what SIGARRA
actually serves. These pages ground the parsers against reality and act as a
regression tripwire when a parser is refactored (or when SIGARRA's markup drifts
and the pages are re-captured).

Pages are stored gzipped (``fixtures/<name>.html.gz``) to keep the repo lean;
:func:`raw` returns the decompressed bytes and :func:`soup` parses them exactly
as :class:`~src.ingestion.scraper.Scraper` does (bytes + ``html.parser``).

Provenance
----------
Captured from the ``horarios_mirror_data`` site mirror (schedule weeks around
Feb-Jun 2026). Teacher/class/room identifiers are public timetable data; a
corpus-wide scan found no raw email addresses. Each fixture is one real page:

===========================  ==================================================
fixture name                 real page / what it exercises
===========================  ==================================================
frameset                     ``index.html`` — the root frameset. ``extract_menu_link``
                             reads only ``<frame NAME="links">`` (note the real,
                             upper-case ``NAME`` and ``%3F``-encoded src).
menu                         ``coluna1.html`` — the full navigation menu: 661
                             teacher links, 51 degrees, 149 rooms (incl. rooms
                             absent from the ``ROOMS`` registry → ``Desconhecido``).
teacher_normal               ``docente_JCR_…`` — happy path: accented name parses
                             correctly; carries 27 red blocks.
teacher_name_is_acronym      ``docente_AA_481933_…`` — a real page whose header
                             sigla (``AJCA``) differs from the acronym node
                             (``AA``); the name is recovered from the header
                             (see ``test_real_pages``).
class_single_session         ``turma_1LEM20_…`` — one multi-class session; a
                             week date *range*.
class_many_sessions          ``turma_M.EA101_…`` — 19 sessions, multiple
                             teachers/classes/types; a *single-date* week
                             (start == end).
room                         ``sala_B001_…`` — a room timetable; red blocks only.
===========================  ==================================================

Modifications: the ``frameset`` fixture has its favicon ``data:`` URI and its
``<noframes>`` block (a ~412 KB duplicate of the menu) stripped — neither is
read by ``extract_menu_link``. All other fixtures are unmodified page bytes.

Refreshing: re-capture the pages from a mirror and re-gzip with
``gzip.compress(page_bytes, mtime=0)`` (deterministic output). Expect the
assertions in ``test_real_pages`` to need updating to the new week's data.
"""

from __future__ import annotations

import gzip
from pathlib import Path

from bs4 import BeautifulSoup

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def raw(name: str) -> bytes:
    """Return the decompressed bytes of the real fixture page called *name*.

    Args:
        name: Fixture stem, e.g. ``"teacher_normal"`` for
            ``fixtures/teacher_normal.html.gz``.
    """
    return gzip.decompress((_FIXTURES_DIR / f"{name}.html.gz").read_bytes())


def soup(name: str) -> BeautifulSoup:
    """Parse a real fixture page the same way the scraper parses a response."""
    return BeautifulSoup(raw(name), "html.parser")
