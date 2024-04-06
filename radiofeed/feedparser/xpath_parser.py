import contextlib
import functools
import io
from collections.abc import Iterator

import lxml.etree


class XPathParser:
    """Parses XML document using XPath."""

    def __init__(self, namespaces: dict[str, str] | None = None) -> None:
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

    def iterfind(self, element: lxml.etree._Element, *paths) -> Iterator:
        """Iterate through paths."""
        for path in paths:
            yield from self._xpath(path)(element)

    def parse(self, *args, **kwargs) -> lxml.etree._Element | None:
        """Returns first matching element, or None if not found."""
        try:
            return next(self.iterparse(*args, **kwargs))
        except (StopIteration, lxml.etree.XMLSyntaxError):
            return None

    def itervalues(self, element: lxml.etree._Element | None, *paths) -> Iterator[str]:
        """Find matching non-empty strings from attributes or text."""
        if element is None:
            return
        with contextlib.suppress(UnicodeDecodeError):
            for value in self.iterfind(element, *paths):
                if isinstance(value, str) and (cleaned := value.strip()):
                    yield cleaned

    def value(self, element: lxml.etree._Element, *paths) -> str | None:
        """Returns first non-empty string value or None if not found."""
        try:
            return next(self.itervalues(element, *paths))
        except StopIteration:
            return None

    @functools.lru_cache(maxsize=60)  # noqa: B019
    def _xpath(self, path: str) -> lxml.etree.XPath:
        return lxml.etree.XPath(path, namespaces=self._namespaces)
