from src.ingestion.schemas.classes import Degree, Teacher
from src.ingestion.scraper import Scraper


def load_class_pages(degrees: list[Degree], scraper: Scraper) -> None:
    """Fetch and populate schedule page data for every class across all degrees.

    For each class in each year of each degree, fetches every schedule page
    linked from the menu and appends the parsed result to the class's ``pages``
    list. This mutates the ``degrees`` structure in place.

    Args:
        degrees: Degree entries whose classes contain links to fetch.
        scraper: Scraper instance used to fetch individual class pages.
    """
    for degree in degrees:
        for year in degree["years"]:
            for class_ in year["classes"]:
                for link in class_["links"]:
                    class_["pages"].append(scraper.get_class_page(link))


def extract_teachers_from_class_pages(degrees: list[Degree]) -> list[Teacher]:
    """Collect all teachers found across every class page in the given degrees.

    Some teachers don't have red blocks and therefore don't appear in the menu's
    teacher links. This function extracts them from the already-loaded class
    pages so they can be merged with the menu-sourced teacher list.

    Args:
        degrees: Degree entries whose classes have their ``pages`` already
            populated (e.g. via :func:`load_class_pages`).

    Returns:
        A flat list of all teacher entries found across every class page.
    """
    return [
        teacher
        for degree in degrees
        for year in degree["years"]
        for class_ in year["classes"]
        for class_page in class_["pages"]
        for teacher in class_page["teachers"]
    ]
