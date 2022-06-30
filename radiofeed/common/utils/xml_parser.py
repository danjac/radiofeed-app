import io

from contextlib import contextmanager

import lxml


def iterparse(content, *tags):

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
def xpath(element, namespaces=None):
    try:
        yield XPath(element, namespaces)
    finally:
        element.clear()


class XPath:
    def __init__(self, element, namespaces=None):
        self.element = element
        self.namespaces = (namespaces or {}) | (element.getparent().nsmap or {})

    def first(self, *paths, default=None):
        try:
            return next(self.iter(*paths))
        except StopIteration:
            return default

    def iter(self, *paths):
        try:
            for path in paths:
                for value in self.element.xpath(path, namespaces=self.namespaces):
                    if cleaned := value.strip():
                        yield cleaned
        except UnicodeDecodeError:
            pass
