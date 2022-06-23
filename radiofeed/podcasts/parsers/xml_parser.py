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
        converter: Callable[[str], T] | None = None,
        default: T | str | None = "",
        required: bool = False,
    ) -> T | str | None:

        for value in self.iter(*paths):
            try:
                return converter(value) if converter else value
            except ValueError:
                continue

        if required:
            raise ValueError
        return default

    def all(self, *paths: str) -> list[str]:
        return list(self.iter(*paths))

    def iter(self, *paths: str) -> Generator[str, None, None]:

        try:
            for path in paths:
                for value in self.element.xpath(path, namespaces=self.namespaces):
                    if cleaned := value.strip():
                        yield cleaned
        except UnicodeDecodeError:
            pass
