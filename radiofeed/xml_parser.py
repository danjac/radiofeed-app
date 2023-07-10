import contextlib
import io
from collections.abc import Iterable, Iterator

import lxml.etree


class XMLParser:
    """Does efficient XPath lookups to find elements and text/attribute values in
    elements."""

    def __init__(self, namespaces: dict[str, str] | None = None):
        self._namespaces = namespaces or {}
        self._xpaths: dict[str, lxml.etree.XPath] = {}

    def iterparse(
        self, content: bytes, root: str, *paths: str
    ) -> Iterator[lxml.etree.Element]:
        """Iterates through elements in XML document with matching tag names."""
        context = lxml.etree.iterparse(
            io.BytesIO(content),
            tag=root,
            encoding="utf-8",
            no_network=True,
            resolve_entities=False,
            recover=True,
            events=("end",),
        )
        for _, element in context:
            yield from self.iterpaths(element, *paths)
            element.clear()
        del context

    def iterpaths(self, element: lxml.etree.Element, *paths: str) -> Iterator:
        """Iterate through elements or strings for each path."""
        for path in paths:
            yield from self._xpath(path)(element)

    def itertext(self, element: lxml.etree.Element, *paths: str) -> Iterator[str]:
        """Iterates through xpaths and returns any non-empty text or attribute values
        matching the path.

        All strings are stripped of extra whitespace. Should skip any unicode errors.
        """
        with contextlib.suppress(UnicodeDecodeError):
            for value in self.iterpaths(element, *paths):
                if isinstance(value, str) and (cleaned := value.strip()):
                    yield cleaned

    def first(self, element: lxml.etree.Element, *paths: str) -> str | None:
        """Returns first matching text or attribute value.

        Tries each path in turn. If no values found returns None.
        """
        try:
            return next(self.itertext(element, *paths))
        except StopIteration:
            return None

    def aslist(self, element: lxml.etree.Element, *paths: str) -> list[str]:
        """Returns path values as list."""
        return list(self.itertext(element, *paths))

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
