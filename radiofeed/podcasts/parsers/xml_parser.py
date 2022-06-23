from __future__ import annotations

import io

from contextlib import contextmanager
from typing import Callable, Generator, TypeVar

import lxml

T = TypeVar("T")


def iterparse(content: bytes, *tags: str) -> Generator[lxml.Element, None, None]:

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


@contextmanager
def xpath(
    element: lxml.etree.Element, namespaces: dict[str, str] | None = None
) -> Generator[XPath, None, None]:
    try:
        yield XPath(element, namespaces)
    finally:
        element.clear()


class XPath:
    def __init__(
        self,
        element: lxml.etree.Element,
        namespaces: dict[str, str] | None = None,
    ):
        self.element = element
        self.namespaces = (namespaces or {}) | (element.getparent().nsmap or {})

    def first(
        self,
        *paths: str,
        converter: Callable[[str | None], T] | None = None,
        default: T | str = "",
        required: bool = False,
    ) -> T | str:
        """Find single attribute or text value. Returns first matching value."""

        try:
            value = next(self.iter(*paths))
            return converter(value) if converter else value
        except (StopIteration, ValueError) as e:
            if required:
                raise ValueError from e
            return default

    def all(self, *paths: str) -> list[str]:
        return list(self.iter(*paths))

    def iter(self, *paths: str) -> Generator[str, None, None]:

        try:
            for path in paths:
                for value in self.element.xpath(path, namespaces=self.namespaces):
                    yield value.strip()
        except UnicodeDecodeError:
            pass
