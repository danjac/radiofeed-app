import functools
import html
import io
import re
from typing import Final

import bs4
import nh3
from bs4.element import NavigableString, Tag
from django.template.defaultfilters import striptags
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

_RE_EXTRA_SPACES: Final = r" +"

_ALLOWED_TAGS: Final = {
    "a",
    "abbr",
    "acronym",
    "address",
    "b",
    "br",
    "code",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "q",
    "s",
    "small",
    "strike",
    "strong",
    "span",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "tt",
    "u",
    "ul",
}

_CLEAN_TAGS: Final = {
    "script",
    "style",
}

_LINK_REL: Final = "noopener noreferrer nofollow"

_TAG_ATTRIBUTES: Final = {
    "a": {
        "target": "_blank",
    },
}

_LINKIFY_PATTERN: Final = re.compile(
    r"(?P<url>(?:(?:https?|ftp)://|www\.)[^\s<]+)",
    re.IGNORECASE,
)
_TRAILING_PUNCTUATION: Final = ",.;:!?)]}"


@mark_safe  # noqa: S308
def render_markdown(content: str) -> str:
    """Scrubs any unwanted HTML tags and attributes and renders Markdown to HTML."""
    if content := content.strip():
        # render Markdown if not already HTML
        if not nh3.is_html(content):
            content = _markdown().render(content)

        return _clean_html(linkify(content))
    return ""


def _clean_html(content: str) -> str:
    return nh3.clean(
        content,
        clean_content_tags=_CLEAN_TAGS,
        link_rel=_LINK_REL,
        set_tag_attribute_values=_TAG_ATTRIBUTES,
        tags=_ALLOWED_TAGS,
    )


def strip_html(content: str) -> str:
    """Scrubs all HTML tags and entities from text.
    Removes content from any style or script tags.

    If content is Markdown, will attempt to render to HTML first.
    """
    return strip_extra_spaces(
        html.unescape(
            striptags(
                render_markdown(content),
            )
        )
    )


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


def linkify(content: str) -> str:
    """Converts URLs to links, if not already in <a> tags."""
    soup = _make_soup(content)
    for node in list(soup.find_all(string=True)):
        _linkify_node(soup, node)
    return str(soup)


def _linkify_node(soup: bs4.BeautifulSoup, node: NavigableString) -> None:
    parent = node.parent
    if not parent or parent.name == "a":
        return

    text = str(node)
    replacements = list(_build_replacements(soup, text))
    if not _has_link_replacement(replacements):
        return

    for replacement in replacements:
        node.insert_before(replacement)
    node.extract()


def _build_replacements(soup: bs4.BeautifulSoup, text: str) -> list[str | Tag]:
    replacements: list[str | Tag] = []
    last_index = 0

    for start, end, url, trailing in _iter_url_matches(text):
        if start > last_index:
            replacements.append(text[last_index:start])

        anchor = soup.new_tag("a", href=_normalize_href(url))
        anchor["rel"] = "nofollow"
        anchor.string = url
        replacements.append(anchor)

        if trailing:
            replacements.append(trailing)

        last_index = end

    if last_index < len(text):
        replacements.append(text[last_index:])

    return replacements


def _has_link_replacement(replacements: list[str | Tag]) -> bool:
    return any(isinstance(item, Tag) for item in replacements)


def _iter_url_matches(text: str) -> list[tuple[int, int, str, str]]:
    matches: list[tuple[int, int, str, str]] = []
    last_index = 0
    for match in _LINKIFY_PATTERN.finditer(text):
        start, end = match.span()
        if start < last_index:
            continue

        url = match.group("url")
        url, trailing = _strip_trailing_punctuation(url)

        if not url:
            continue

        matches.append((start, end, url, trailing))
        last_index = end
    return matches


def _strip_trailing_punctuation(url: str) -> tuple[str, str]:
    trailing = ""
    while url and url[-1] in _TRAILING_PUNCTUATION:
        trailing = url[-1] + trailing
        url = url[:-1]
    return url, trailing


def _normalize_href(url: str) -> str:
    return url if not url.lower().startswith("www.") else f"https://{url}"


def _make_soup(content: str) -> bs4.BeautifulSoup:
    with io.StringIO(content) as fp:
        return bs4.BeautifulSoup(fp, "html.parser")


@functools.cache
def _re_extra_spaces() -> re.Pattern:
    return re.compile(_RE_EXTRA_SPACES)


@functools.cache
def _markdown():
    return MarkdownIt(
        "commonmark",
        {
            "linkify": True,
            "typographer": True,
        },
    ).enable(
        [
            "linkify",
            "replacements",
            "smartquotes",
        ]
    )
