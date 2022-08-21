from __future__ import annotations

import io

from contextlib import contextmanager
from typing import Iterable, Iterator, TypeAlias

import lxml  # nosec

Namespaces: TypeAlias = dict[str, str]


def parse_xml(content: bytes, *tags: str) -> Iterator[lxml.etree.Element]:
    """Iterates through elements in XML document with matching tag names.

    Args:
        content: XML document
        `*tags`: tag names
    """
    for _, element in lxml.etree.iterparse(
        io.BytesIO(content),
        encoding="utf-8",
        no_network=True,
        resolve_entities=False,
        recover=True,
        events=("end",),
    ):
        if element.tag in tags:
            yield element


class XPathFinder:
    """Wrapper class for doing XPath lookups to find text or attribute values on an XML element.

    Args:
        element: the root element you want to search
        namespaces: dict of XML namespaces
    """

    def __init__(
        self, element: lxml.etree.Element, namespaces: Namespaces | None = None
    ):
        self._element = element
        self._namespaces = (namespaces or {}) | (element.getparent().nsmap or {})

    def first(self, *paths) -> str | None:
        """Returns first matching text or attribute value.

        Tries each path in turn. If no values found returns `default`.

        Args:
            `*paths` (str): list of XPath paths to search through in order

        Returns:
            string of text/attribute, or None if not found
        """
        try:
            return next(self.iter(*paths))
        except StopIteration:
            return None

    def iter(self, *paths) -> Iterator[str]:
        """Iterates through xpaths and returns any non-empty text or attribute values matching the path.

        All strings are stripped of extra whitespace. Should skip any unicode errors.

        Args:
            `*paths`: list of XPath paths to search through in order
        """
        try:
            for path in paths:
                for value in self._element.xpath(path, namespaces=self._namespaces):
                    if cleaned := value.strip():
                        yield cleaned
        except UnicodeDecodeError:
            pass

    def to_list(self, *paths: str | Iterable) -> list[str]:
        """Returns path values as list."""
        return list(self.iter(*paths))

    def to_dict(self, **fields: str | Iterable) -> dict[str, str | None]:
        """Returns dict with each field mapped to one or more xpaths.

        Example of usage:

        .. code block:: python

            finder.to_dict(
                title="title/text()",
                cover_url=[
                    "itunes:image/@href",
                    "image/url/text()",
                ]
            )

        This should return e.g.:

        .. code block:: python

            {
                "title": "Sample title",
                "cover_url": "/path/to/url"
            }

        As this calls `first()` will default to None for any fields that cannot be found.

        Args:
            `**fields`: dict of field and xpath mapping(s)
        """
        return {
            field: self.first(*[xpaths] if isinstance(xpaths, str) else xpaths)
            for field, xpaths in fields.items()
        }


@contextmanager
def xpath_finder(
    element: lxml.etree.Element, namespaces: Namespaces | None = None
) -> Iterator[XPathFinder]:
    """Returns XPathFinder instance for an XML element as a context manager.

    Args:
        element: the root element you want to search
        namespaces: dict of XML namespaces
    """
    try:
        yield XPathFinder(element, namespaces)
    finally:
        element.clear()
