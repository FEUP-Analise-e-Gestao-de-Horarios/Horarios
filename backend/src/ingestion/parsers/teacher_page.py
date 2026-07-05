import re

from bs4 import BeautifulSoup, NavigableString


def extract_teacher_info(soup: BeautifulSoup) -> tuple[str, str, int]:
    """Extract teacher acronym, name, and code from a parsed teacher page.

    Parses the ``<td class="cabtitulo">`` header cell, whose ``<br>``-separated
    text nodes are ``{header}``, ``{acronym}``, ``{code}`` (any further nodes,
    such as a trailing ``Semanas: …`` range, are ignored). ``{header}`` is
    ``"{sigla} - {name}"``; the displayed *sigla* is usually the acronym but may
    extend or differ from it, so the name is taken as the text after the first
    ``-`` separator (peeling a matching acronym prefix first, so a longer sigla's
    own separator is the one used). When the header has no name part (it is just
    a code), the acronym is used as the name.

    Args:
        soup: Parsed HTML of the teacher page.

    Returns:
        A tuple of (acronym, name, code) where:
        - acronym: Short identifier for the teacher (e.g. "ABC").
        - name: Full name, cleaned of punctuation. Falls back to the acronym
          when the header carries no name part.
        - code: Number identifying the teacher.

    Raises:
        ValueError: If ``<td class="cabtitulo">`` is not found, or it does not
            carry at least three text nodes (header, acronym, code).
    """
    td = soup.find("td", {"class": "cabtitulo"})
    if td is None:
        raise ValueError("Could not find <td class='cabtitulo'>")

    text_nodes = [
        text for node in td.contents if isinstance(node, NavigableString) and (text := node.strip())
    ]
    if len(text_nodes) < 3:
        raise ValueError(
            f"Expected at least 3 text nodes in 'cabtitulo', found {len(text_nodes)}: {text_nodes}",
        )

    header, acronym, raw_code = text_nodes[0], text_nodes[1], text_nodes[2]

    # The header is "{sigla}[ - ]{name}". The displayed sigla is usually the
    # acronym, but it may extend it ("AMMTB" vs "AMM"), differ entirely ("AJCA"
    # vs "AA"), or itself contain " - " ("DCC - ACM"). When the acronym prefixes
    # the header, peel it off first so only the sigla's own separator is left;
    # otherwise the sigla is a single token and the first "-" splits it from the
    # name. Split on the *first* separator, not the last, so a name that itself
    # contains " - " keeps all of its parts.
    body = header[len(acronym) :] if header.startswith(acronym) else header
    name = body.split("-", 1)[1] if "-" in body else ""

    name = re.sub(r"[^\w\s]", "", name).strip()
    if not name:  # header carried no name part: use the acronym
        name = re.sub(r"[^\w\s]", "", acronym).strip() or acronym

    return acronym, name, int(raw_code)
