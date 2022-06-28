import pathlib

import pytest

from radiofeed.podcasts.parsers import opml_parser


class TestOpmlParser:
    def read_mock_file(self, mock_filename):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()

    def test_empty(self):
        with pytest.raises(opml_parser.OpmlParserError):
            list(opml_parser.parse_opml(b""))

    def test_invalid_xml(self):
        outlines = list(opml_parser.parse_opml(b"not opml content"))
        assert len(outlines) == 0

    def test_invalid_outline(self):
        outlines = list(
            opml_parser.parse_opml(self.read_mock_file("feeds_with_invalid.opml"))
        )
        assert len(outlines) == 10

    def test_ok(self):
        outlines = list(opml_parser.parse_opml(self.read_mock_file("feeds.opml")))
        assert len(outlines) == 11
