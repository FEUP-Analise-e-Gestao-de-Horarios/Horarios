import re

from bs4 import BeautifulSoup, NavigableString


def extract_teacher_info(soup: BeautifulSoup) -> tuple[str, str, int]:
    """Extract teacher acronym, name, and code from a parsed teacher page.

    Parses the ``<td class="cabtitulo">`` header cell, whose ``<br>``-separated
    text nodes are ``{header}``, ``{acronym}``, ``{code}`` (any further nodes,
    such as a trailing ``Semanas: …`` range, are ignored). ``{header}`` is
    ``"{sigla} - {name}"``; the displayed *sigla* is usually the acronym but may
    extend or differ from it, so the name is taken as the text after the sigla's
    own separator (peeling a matching acronym prefix first, then preferring the
    last ``" - "`` so a multi-token sigla is fully consumed). When the acronym
    prefixes the header but no separator follows, the residual after peeling is
    the name (``"MJMS Maria João …"``); when the header is just a code with no
    name part at all, the acronym is used as the name.

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
    # vs "AA"), or itself contain " - " ("DCC - ACM"). Peel a matching acronym
    # prefix, then take the name after the sigla's own separator: prefer the
    # last " - " so a multi-token sigla ("DCC - ACM") is fully consumed, fall
    # back to a bare "-" only when the sigla runs straight into it ("AJCA-Name")
    # rather than a hyphen sitting inside the name ("MJMS Maria João Sá-Carneiro"),
    # and when the acronym runs straight into a whitespace-separated name
    # ("MJMS Maria João …") keep the residual. A sigla that differs entirely and
    # carries no separator has no name part.
    peeled = header.startswith(acronym)
    body = header[len(acronym) :] if peeled else header
    if " - " in body:
        name = body.rsplit(" - ", 1)[1]
    elif "-" in body and " " not in body.split("-", 1)[0]:
        name = body.split("-", 1)[1]
    elif peeled:
        name = body
    else:
        name = ""

    name = re.sub(r"[^\w\s'-]", "", name).strip()
    if not name:  # header carried no name part: use the acronym
        name = re.sub(r"[^\w\s'-]", "", acronym).strip() or acronym

    return acronym, name, int(raw_code)
