"""Unit tests for :mod:`src.ingestion.utils`.

Two helpers bridge the scraper and the manager:

* ``load_class_pages`` — fetches every week page for every class and appends the
  parsed result onto the class's ``pages`` list, mutating ``degrees`` in place.
* ``extract_teachers_from_class_pages`` — flattens every teacher entry found
  across all already-loaded class pages (used to recover teachers who have no
  red blocks and thus no menu link).
"""

from src.ingestion.schemas.classes import ClassPage, Degree
from src.ingestion.utils import extract_teachers_from_class_pages, load_class_pages


class _FakeScraper:
    """Returns a canned ``ClassPage`` per link and records the fetch order."""

    def __init__(self, pages: dict[str, ClassPage]) -> None:
        self._pages = pages
        self.requested: list[str] = []

    def get_class_page(self, link: str) -> ClassPage:
        self.requested.append(link)
        return self._pages[link]


def _blank_page(teachers: list[dict]) -> ClassPage:
    return {
        "start_date": None,  # type: ignore[typeddict-item]
        "end_date": None,  # type: ignore[typeddict-item]
        "teachers": teachers,
        "subjects": [],
        "sessions": [],
        "red_blocks": [],
    }


def _degrees(links_by_class: dict[str, list[str]]) -> list[Degree]:
    return [
        {
            "acronym": "LEIC",
            "name": "Curso",
            "years": [
                {
                    "number": 1,
                    "classes": [
                        {"code": code, "links": links, "pages": []}
                        for code, links in links_by_class.items()
                    ],
                },
            ],
        },
    ]


def test_load_class_pages_populates_every_link() -> None:
    degrees = _degrees({"1LEIC01": ["a.html", "b.html"], "1LEIC02": ["c.html"]})
    scraper = _FakeScraper(
        {
            "a.html": _blank_page([{"code": 1, "acronym": "A", "name": "A"}]),
            "b.html": _blank_page([]),
            "c.html": _blank_page([{"code": 2, "acronym": "B", "name": "B"}]),
        },
    )

    load_class_pages(degrees, scraper)  # type: ignore[arg-type]

    classes = degrees[0]["years"][0]["classes"]
    assert len(classes[0]["pages"]) == 2
    assert len(classes[1]["pages"]) == 1
    assert scraper.requested == ["a.html", "b.html", "c.html"]


def test_load_class_pages_no_links_leaves_pages_empty() -> None:
    degrees = _degrees({"1LEIC01": []})
    scraper = _FakeScraper({})

    load_class_pages(degrees, scraper)  # type: ignore[arg-type]

    assert degrees[0]["years"][0]["classes"][0]["pages"] == []
    assert scraper.requested == []


def test_extract_teachers_flattens_across_pages() -> None:
    degrees = _degrees({"1LEIC01": ["a.html"], "1LEIC02": ["c.html"]})
    scraper = _FakeScraper(
        {
            "a.html": _blank_page(
                [
                    {"code": 1, "acronym": "A", "name": "Alpha"},
                    {"code": 2, "acronym": "B", "name": "Beta"},
                ],
            ),
            "c.html": _blank_page([{"code": 3, "acronym": "C", "name": "Gamma"}]),
        },
    )
    load_class_pages(degrees, scraper)  # type: ignore[arg-type]

    teachers = extract_teachers_from_class_pages(degrees)

    assert [t["code"] for t in teachers] == [1, 2, 3]


def test_extract_teachers_empty_when_no_pages_loaded() -> None:
    degrees = _degrees({"1LEIC01": ["a.html"]})
    assert extract_teachers_from_class_pages(degrees) == []
