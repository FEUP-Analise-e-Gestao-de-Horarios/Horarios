"""Shared fake ``requests.Session``/response doubles for the ingestion tests.

The scraper's only network dependency is ``self._session`` (a
``requests.Session``); swapping it for :class:`FakeSession` lets tests drive the
scraper without touching the network. Bodies may be ``str`` (synthetic markup
built by :mod:`_html`) or raw ``bytes`` (real captured pages from
:mod:`_fixtures`).
"""

from __future__ import annotations

import requests


class FakeResponse:
    """Canned response exposing the ``.content`` bytes and ``raise_for_status``
    that :meth:`~src.ingestion.scraper.Scraper._request` reads.

    ``body`` may be ``str`` (encoded to utf-8) or raw ``bytes``.
    """

    def __init__(self, body: str | bytes, status_ok: bool = True) -> None:
        self.content = body.encode("utf-8") if isinstance(body, str) else body
        self._status_ok = status_ok

    def raise_for_status(self) -> None:
        if not self._status_ok:
            raise requests.HTTPError("non-2xx")


class FakeSession:
    """Routes request URLs to canned responses and records every call.

    ``pages`` maps a full request URL (``base_url + path``) to its body: a
    ``str``/``bytes`` payload, or a :class:`FakeResponse` when a non-2xx status
    is needed. A GET for a URL not in the map raises ``AssertionError`` so an
    unexpected fetch fails loudly rather than silently serving the wrong page.
    """

    def __init__(self, pages: dict[str, FakeResponse | str | bytes]) -> None:
        self._pages = {
            url: body if isinstance(body, FakeResponse) else FakeResponse(body)
            for url, body in pages.items()
        }
        self.calls: list[tuple[str, object]] = []
        self.closed = False

    def get(self, url: str, timeout: object = None) -> FakeResponse:
        self.calls.append((url, timeout))
        if url not in self._pages:
            raise AssertionError(f"unexpected URL requested: {url!r}")
        return self._pages[url]

    def close(self) -> None:
        self.closed = True
