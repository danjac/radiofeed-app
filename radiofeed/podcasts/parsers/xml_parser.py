from __future__ import annotations

import io

from typing import Generator

import lxml


def iterparse(content: bytes) -> Generator[lxml.Element, None, None]:

    for _, element in lxml.etree.iterparse(
        io.BytesIO(content),
        encoding="utf-8",
        no_network=True,
        resolve_entities=False,
        recover=True,
        events=("end",),
    ):
        yield element


class XPathFinder:
    def __init__(
        self, element: lxml.etree.Element, namespaces: dict[str, str] | None = None
    ):
        self.element = element
        self.namespaces = namespaces

    def first(self, *paths: str, default: str = "", required: bool = False) -> str:
        """Find single attribute or text value. Returns first matching value."""

        for path in paths:
            try:
                return self.all(path)[0]
            except IndexError:
                continue
        if required:
            raise ValueError(f"No value found for {paths}")
        return default

    def all(self, path: str) -> list[str]:
        try:
            return [
                value.strip()
                for value in self.element.xpath(path, namespaces=self.namespaces)
            ]
        except UnicodeDecodeError:
            return []
