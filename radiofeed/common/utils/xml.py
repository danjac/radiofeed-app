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

    def first(self, *paths):
        """Returns first matching text or attribute value.

        Tries each path in turn. If no values found returns `default`.

        Args:
            `*paths` (str): list of XPath paths to search through in order

        Returns:
            str | None: string of text/attribute, or None if not found
        """
        try:
            return next(self.iter(*paths))
        except StopIteration:
            return None

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

    def to_dict(self, **fields):
        """Returns a dict with each field mapped to one or more xpaths.

        Example:

        .. code block:: python

            finder.to_dict(
                title="title/text()",
                cover_url=[
                    "itunes:image/@href",
                    "image/url/text()",
                ]
            )

        This should return e.g.:

        .. code block:: python

            {
                "title": "Sample title",
                "cover_url": "/path/to/url"
            }

        As this calls `first()` will default to None for any fields that cannot be found.

        Args:
            `**fields` (dict[str, str | Iterable]): dict of field and xpath mapping(s)

        Returns:
            dict[str, str | None]
        """
        return {
            field: self.first(*[xpaths] if isinstance(xpaths, str) else xpaths)
            for field, xpaths in fields.items()
        }
