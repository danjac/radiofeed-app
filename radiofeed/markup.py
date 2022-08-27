from __future__ import annotations

import re

from django.utils.safestring import mark_safe
from markdown import markdown as _markdown

from radiofeed import cleaners

_HTML_RE = re.compile(r"^(<\/?[a-zA-Z][\s\S]*>)+", re.UNICODE)


def markdown(value: str | None) -> str:
    """Returns safe Markdown rendered string. If content is already HTML will pass as-is."""
    if value := cleaners.strip_whitespace(value):

        return mark_safe(  # nosec
            cleaners.clean(value if _HTML_RE.match(value) else _markdown(value))
        )
    return ""
