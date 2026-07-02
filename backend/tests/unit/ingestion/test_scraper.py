"""Unit tests for :class:`src.ingestion.scraper.Scraper`.

The scraper is the HTTP boundary: it fetches pages with a shared
``requests.Session`` and dispatches each to the right parser. These tests swap
the session for a hand-rolled fake so no network is touched, then assert the
scraper (a) builds request URLs from ``base_url + path``, (b) raises on non-2xx
responses, and (c) returns the parser output for each page type.
"""

import datetime

import pytest
import requests

from src.ingestion.schemas.misc import WeekDay
from src.ingestion.scraper import Scraper
from tests.unit.ingestion import _html as H


class _FakeResponse:
    def __init__(self, content: str, status_ok: bool = True) -> None:
        self.content = content.encode("utf-8")
        self._status_ok = status_ok

    def raise_for_status(self) -> None:
        if not self._status_ok:
            raise requests.HTTPError("non-2xx")


class _FakeSession:
    """Maps request URLs to canned responses and records every call."""

    def __init__(self, pages: dict[str, _FakeResponse]) -> None:
        self._pages = pages
        self.calls: list[tuple[str, object]] = []
        self.closed = False

    def get(self, url: str, timeout: object = None) -> _FakeResponse:
        self.calls.append((url, timeout))
        if url not in self._pages:
            raise AssertionError(f"unexpected URL requested: {url!r}")
        return self._pages[url]

    def close(self) -> None:
        self.closed = True


def _scraper(base_url: str, pages: dict[str, _FakeResponse]) -> tuple[Scraper, _FakeSession]:
    scraper = Scraper(base_url)
    fake = _FakeSession(pages)
    scraper._session = fake  # type: ignore[assignment]
    return scraper, fake


# ---------------------------------------------------------------------------
# -- _request
# ---------------------------------------------------------------------------


def test_request_builds_url_and_applies_timeout() -> None:
    scraper, fake = _scraper(
        "https://sigarra.example/",
        {"https://sigarra.example/page": _FakeResponse("<html><body>ok</body></html>")},
    )
    soup = scraper._request("page")

    assert soup.get_text(strip=True) == "ok"
    (url, timeout) = fake.calls[0]
    assert url == "https://sigarra.example/page"
    assert timeout == Scraper._DEFAULT_TIMEOUT


def test_request_raises_on_http_error() -> None:
    scraper, _ = _scraper(
        "https://x/",
        {"https://x/boom": _FakeResponse("", status_ok=False)},
    )
    with pytest.raises(requests.HTTPError):
        scraper._request("boom")


def test_request_concatenates_without_urljoin_normalization() -> None:
    # _request does `self.base_url + path` with NO urljoin: a base_url without a
    # trailing slash concatenates directly, so "https://x" + "menu" == "https://xmenu".
    scraper, fake = _scraper(
        "https://x",
        {"https://xmenu": _FakeResponse("<html><body>ok</body></html>")},
    )
    scraper._request("menu")

    (url, _timeout) = fake.calls[0]
    assert url == "https://xmenu"


def test_request_does_not_normalize_leading_slash_path() -> None:
    # A leading-slash path is NOT collapsed against the base_url's own path;
    # it is appended verbatim, producing a doubled slash rather than a reset.
    scraper, fake = _scraper(
        "https://x/base",
        {"https://x/base/menu": _FakeResponse("<html><body>ok</body></html>")},
    )
    scraper._request("/menu")

    (url, _timeout) = fake.calls[0]
    assert url == "https://x/base/menu"


# ---------------------------------------------------------------------------
# -- read_menu
# ---------------------------------------------------------------------------


def test_read_menu_fetches_root_then_menu_frame() -> None:
    scraper, fake = _scraper(
        "https://x/",
        {
            "https://x/": _FakeResponse(H.frame_page("menu.html")),
            "https://x/menu.html": _FakeResponse(H.menu_page()),
        },
    )
    teacher_links, degrees, rooms = scraper.read_menu()

    assert teacher_links == ["teacher/abc.html"]
    assert [d["acronym"] for d in degrees] == ["LEIC"]
    assert [r["name"] for r in rooms] == ["B001"]
    # Two requests in order: the root page, then the menu frame it points at.
    assert [url for url, _ in fake.calls] == ["https://x/", "https://x/menu.html"]


def test_read_menu_raises_when_menu_frame_fetch_fails() -> None:
    # read_menu makes two sequential requests: the root frame page (ok) and then
    # the extracted menu frame. A failure of the SECOND request must propagate
    # and is not swallowed by the successful first request.
    scraper, fake = _scraper(
        "https://x/",
        {
            "https://x/": _FakeResponse(H.frame_page("menu.html")),
            "https://x/menu.html": _FakeResponse("", status_ok=False),
        },
    )
    with pytest.raises(requests.HTTPError):
        scraper.read_menu()

    # Both requests were attempted, in order, and the timeout is applied to the
    # second (menu frame) call as well as the first.
    assert [url for url, _ in fake.calls] == ["https://x/", "https://x/menu.html"]
    assert fake.calls[1][1] == Scraper._DEFAULT_TIMEOUT


# ---------------------------------------------------------------------------
# -- page fetchers
# ---------------------------------------------------------------------------


def test_get_teacher_page() -> None:
    scraper, _ = _scraper(
        "https://x/",
        {
            "https://x/t/abc.html": _FakeResponse(
                H.teacher_page(
                    red_time_rows=[[H.time_cell("09:00"), H.red_cell(), H.empty_cell()]],
                ),
            ),
        },
    )
    teacher = scraper.get_teacher_page("t/abc.html")

    assert teacher == {
        "acronym": "ABC",
        "name": "Ada Berta Costa",
        "code": 123,
        "red_blocks": [(900, WeekDay.MONDAY)],
    }


def test_get_class_page() -> None:
    scraper, _ = _scraper(
        "https://x/",
        {"https://x/c/w1.html": _FakeResponse(H.class_page())},
    )
    page = scraper.get_class_page("c/w1.html")

    assert page["start_date"] == datetime.date(2025, 9, 15)
    assert page["end_date"] == datetime.date(2025, 9, 21)
    assert [t["acronym"] for t in page["teachers"]] == ["ABC"]
    assert [s["acronym"] for s in page["subjects"]] == ["PROG"]
    assert len(page["sessions"]) == 1
    assert page["red_blocks"] == []


def test_get_room_page_returns_red_blocks() -> None:
    scraper, _ = _scraper(
        "https://x/",
        {
            "https://x/r/b1.html": _FakeResponse(
                H.room_page(red_time_rows=[[H.time_cell("14:00"), H.empty_cell(), H.red_cell()]]),
            ),
        },
    )
    assert scraper.get_room_page("r/b1.html") == [(1400, WeekDay.TUESDAY)]


def test_close_closes_session() -> None:
    scraper, fake = _scraper("https://x/", {})
    scraper.close()
    assert fake.closed is True
