import contextlib
import io
from collections.abc import Iterator

import lxml


class XPathParser:
    """Parses XML document using XPath."""

    def __init__(self, namespaces: dict[str, str] | None = None) -> None:
        self._xpaths: dict[str, lxml.etree.XPath] = {}
        self._namespaces = namespaces

    def iterparse(
        self, content: bytes, tag: str | None = None, *paths: str
    ) -> Iterator:
        """Parses document into iterable of paths."""
        for _, element in lxml.etree.iterparse(
            io.BytesIO(content),
            tag=tag,
            encoding="utf-8",
            no_network=True,
            resolve_entities=False,
            recover=True,
            events=("end",),
        ):
            try:
                if paths:
                    yield from self.iterfind(element, *paths)
            finally:
                element.clear()

    def iterfind(self, element: lxml.etree.Element, *paths) -> Iterator:
        """Iterate through paths."""
        for path in paths:
            yield from self._xpath(path)(element)

    def iterstrings(self, element: lxml.etree.Element, *paths) -> Iterator[str]:
        """Find matching non-empty strings from attributes or text."""
        with contextlib.suppress(UnicodeDecodeError):
            for value in self.iterfind(element, *paths):
                if isinstance(value, str) and (cleaned := value.strip()):
                    yield cleaned

    def string(self, element: lxml.etree.Element, *paths) -> str | None:
        """Returns first non-empty string value or None if not found."""
        try:
            return next(self.iterstrings(element, *paths))
        except StopIteration:
            return None

    def _xpath(self, path: str) -> lxml.etree.XPath:
        if path in self._xpaths:
            return self._xpaths[path]

        xpath = lxml.etree.XPath(path, namespaces=self._namespaces)
        self._xpaths[path] = xpath
        return xpath
