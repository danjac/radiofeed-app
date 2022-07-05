import io

from contextlib import contextmanager

import lxml


def parse_xml(content, *tags):
    """Iterates through elements in XML document with matching tag names.

    Args:
        content (bytes): XML document
        `*tags` (str): tag names

    Yields:
        lxml.etree.Element
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


@contextmanager
def xpath_finder(element, namespaces=None):
    """Returns XPathFinder instance for an XML element as a context manager.

    Args:
        element (lxml.etree.Element): the root element you want to search
        namespaces (dict | None): dict of XML namespaces

    Yields:
        XPathFinder
    """
    try:
        yield XPathFinder(element, namespaces)
    finally:
        element.clear()


class XPathFinder:
    """Wrapper class for doing XPath lookups to find text or attribute values on an XML element.

    Args:
        element (lxml.etree.Element): the root element you want to search
        namespaces (dict | None): dict of XML namespaces
    """

    def __init__(self, element, namespaces=None):
        self._element = element
        self._namespaces = (namespaces or {}) | (element.getparent().nsmap or {})

    def first(self, *paths, default=None):
        """Returns first matching text or attribute value.

        Tries each path in turn. If no values found returns `default`.

        Args:
            `*paths` (str): list of XPath paths to search through in order
            default (Any):  value returned if no result found

        Returns:
            Any: string of text/attribute, or default value if none found
        """
        try:
            return next(self.iter(*paths))
        except StopIteration:
            return default

    def iter(self, *paths):
        """Iterates through xpaths and returns any non-empty text or attribute values matching the path.

        All strings are stripped of extra whitespace. Should skip any unicode errors.

        Args:
            `*paths` (str): list of XPath paths to search through in order

        Yields:
            str
        """
        try:
            for path in paths:
                for value in self._element.xpath(path, namespaces=self._namespaces):
                    if cleaned := value.strip():
                        yield cleaned
        except UnicodeDecodeError:
            pass
