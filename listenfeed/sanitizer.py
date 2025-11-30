import functools
import html
import re
from typing import Final

from django.template.defaultfilters import striptags

from listenfeed.markdown import markdownify

_RE_EXTRA_SPACES: Final = r" +"


def strip_html(content: str) -> str:
    """Scrubs all HTML tags and entities from text.
    Removes content from any style or script tags.

    If content is Markdown, will attempt to render to HTML first.
    """
    return strip_extra_spaces(html.unescape(striptags(markdownify(content))))


def strip_extra_spaces(value: str) -> str:
    """Removes any extra linebreaks and spaces."""
    lines = [
        line
        for line in [
            _re_extra_spaces().sub(" ", line).strip() for line in value.splitlines()
        ]
        if line
    ]
    return "\n".join(lines)


@functools.cache
def _re_extra_spaces() -> re.Pattern:
    return re.compile(_RE_EXTRA_SPACES)
