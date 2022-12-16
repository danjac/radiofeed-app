from __future__ import annotations

import io

from typing import Iterable, Iterator, TypeAlias

import lxml.etree  # nosec

Namespaces: TypeAlias = dict[str, str]


def xml_iterparse(content: bytes, *tags: str) -> Iterator[lxml.etree.Element]:
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
    """Wrapper class for doing XPath lookups to find text or attribute values on an XML element."""

    def __init__(self, namespaces: Namespaces | None = None):
        self._namespaces = namespaces or {}
        self._xpaths: dict[str, lxml.etree.XPath] = {}

    def iterparse(
        self, content: bytes, root: str, *paths: str
    ) -> Iterator[lxml.etree.Element]:
        """Iterates through elements in XML document with matching tag names."""
        context = lxml.etree.iterparse(
            io.BytesIO(content),
            encoding="utf-8",
            no_network=True,
            resolve_entities=False,
            recover=True,
            tag=root,
            events=("end",),
        )
        for _, element in context:
            yield from self.findall(element, *paths)
            element.clear()
            for ancestor in self.findall(element, "ancestor-or-self::*"):
                while ancestor.getprevious() is not None:
                    del ancestor.getparent()[0]
        del context

    def iter(self, element: lxml.etree.Element, *paths: str) -> Iterator[str]:
        """Iterates through xpaths and returns any non-empty text or attribute values matching the path.

        All strings are stripped of extra whitespace. Should skip any unicode errors.
        """
        try:
            for path in paths:
                for value in self._xpath(path)(element):
                    if cleaned := value.strip():
                        yield cleaned
        except UnicodeDecodeError:
            pass

    def findall(
        self, element: lxml.etree.Element, *paths: str
    ) -> Iterator[lxml.etree.Element]:
        """Iterate through elements rather than strings."""
        for path in paths:
            yield from self._xpath(path)(element)

    def first(self, element: lxml.etree.Element, *paths: str) -> str | None:
        """Returns first matching text or attribute value.

        Tries each path in turn. If no values found returns `default`.
        """
        try:
            return next(self.iter(element, *paths))
        except StopIteration:
            return None

    def aslist(self, element: lxml.etree.Element, *paths: str) -> list[str]:
        """Returns path values as list."""
        return list(self.iter(element, *paths))

    def asdict(
        self, element: lxml.etree.Element, **fields: str | Iterable
    ) -> dict[str, str | None]:
        """Returns dict with each field mapped to one or more xpaths."""
        return {
            field: self.first(element, *[xpaths] if isinstance(xpaths, str) else xpaths)
            for field, xpaths in fields.items()
        }

    def _xpath(self, path: str) -> lxml.etree.XPath:
        if not (xpath := self._xpaths.get(path)):
            self._xpaths[path] = xpath = lxml.etree.XPath(
                path, namespaces=self._namespaces
            )
        return xpath
