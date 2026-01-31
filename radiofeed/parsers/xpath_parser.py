import contextlib
import functools
import io
from typing import TYPE_CHECKING, TypeAlias

import lxml.etree

if TYPE_CHECKING:
    from collections.abc import Iterator

Namespaces: TypeAlias = tuple[tuple[str, str], ...]
OptionalXmlElement: TypeAlias = lxml.etree._Element | None


class XPathParser:
    """Parses XML document using XPath."""

    def __init__(self, namespaces: Namespaces = ()) -> None:
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
                with contextlib.suppress(AttributeError, TypeError):
                    while element.getprevious() is not None:
                        del element.getparent()[0]

    def find(self, *args, **kwargs) -> OptionalXmlElement:
        """Returns first matching element, or None if not found."""
        try:
            return next(self.iterparse(*args, **kwargs))
        except (StopIteration, lxml.etree.XMLSyntaxError):
            return None

    def value(self, element: OptionalXmlElement, *paths: str) -> str | None:
        """Returns first non-empty string value or None if not found."""
        try:
            return next(self.itervalues(element, *paths))
        except StopIteration:
            return None

    def iterfind(self, element: OptionalXmlElement, *paths: str) -> Iterator:
        """Iterate through paths."""
        if element is None:
            return
        for path in paths:
            yield from _xpath(path, self._namespaces)(element)

    def itervalues(self, element: OptionalXmlElement, *paths: str) -> Iterator[str]:
        """Find matching non-empty strings from attributes or text."""
        with contextlib.suppress(UnicodeDecodeError):
            for value in self.iterfind(element, *paths):
                if isinstance(value, str) and (cleaned := value.strip()):
                    yield cleaned


@functools.cache
def _xpath(path: str, namespaces: Namespaces) -> lxml.etree.XPath:
    return lxml.etree.XPath(path, namespaces=namespaces)
