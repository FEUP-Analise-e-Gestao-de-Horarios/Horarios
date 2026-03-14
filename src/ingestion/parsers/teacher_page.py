import re

from bs4 import BeautifulSoup


def extract_teacher_info(soup: BeautifulSoup) -> tuple[str, str, int]:
    """Extract teacher acronym, name, and code from a parsed teacher page.

    Parses the `<td class="cabtitulo">` element, which contains the teacher's
    acronym, full name, and numeric code separated by `<br/>` tags.

    Args:
        soup: Parsed HTML of the teacher page.

    Returns:
        A tuple of (acronym, name, code) where:
        - acronym: Short identifier for the teacher (e.g. "ABC").
        - name: Full name, cleaned of punctuation. Falls back to acronym if empty.
        - code: Numeric string identifying the teacher.

    Raises:
        ValueError: If `<td class="cabtitulo">` is not found in the page.
    """
    td = soup.find("td", {"class": "cabtitulo"})
    if td is None:
        raise ValueError("Could not find <td class='cabtitulo'>")

    content = str(td.contents)
    if '"' in content:
        first = content.split('"')[1]
        acronym = content.split("<br/>, '")[1].split("'")[0]
        name = first[len(acronym) :] if acronym in first else ""
        code = int(content.split("<br/>, '")[2].split("'")[0])
    else:
        content = content.split("', <br/>, '")
        acronym = content[1].split("'")[0]
        name = content[0][len(acronym) + 2 :] if acronym in content[0] else ""
        code = int(content[2].split("'")[0])

    if " - " in name:
        name = name[3:]
    if name == "":
        name = acronym
    name = re.sub(r"[^\w\s]", "", name)

    return acronym, name, code
