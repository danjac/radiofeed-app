import html

from django.template.defaultfilters import striptags

from radiofeed import markdown


def strip_html(value: str) -> str:
    """Scrubs all HTML tags and entities from text."""
    return html.unescape(striptags(markdown.render(value)))
