import html
import re
from collections.abc import Iterator
from typing import Final

from django.template.defaultfilters import striptags

from radiofeed import markdown

_RE_EXTRA_SPACES: Final = r" +"


def strip_html(value: str) -> str:
    """Scrubs all HTML tags and entities from text.
    Removes content from any style or script tags.

    If content is Markdown, will attempt to render to HTML first.
    """
    return strip_extra_spaces(html.unescape(striptags(markdown.render(value))))


def strip_extra_spaces(value: str) -> str:
    """Removes any extra linebreaks and spaces."""
    return "\n".join(_strip_spaces_from_lines(value)).strip()


def _strip_spaces_from_lines(value: str) -> Iterator[str]:
    for line in value.split("\n"):
        if stripped := re.sub(_RE_EXTRA_SPACES, " ", line).strip():
            yield stripped
