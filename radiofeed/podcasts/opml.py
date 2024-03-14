from collections.abc import Iterator
from typing import IO

import bs4


def parse_opml(fp: IO) -> Iterator[str]:
    """Parse OPML document and return podcast URLs"""
    soup = bs4.BeautifulSoup(fp.read(), features="xml")
    for outline in soup.find_all("outline"):
        if url := outline.get("xmlUrl"):
            yield url
