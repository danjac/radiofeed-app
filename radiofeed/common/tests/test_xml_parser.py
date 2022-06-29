import pathlib

import pytest

from radiofeed.common import xml_parser


class TestXPath:
    def read_mock_file(self, mock_filename="rss_mock.xml"):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()

    @pytest.fixture
    def channel(self):
        return next(xml_parser.iterparse(self.read_mock_file(), "channel"))

    def test_iter(self, channel):
        assert list(xml_parser.XPath(channel).iter("title/text()")) == [
            "Mysterious Universe"
        ]

    def test_first_exists(self, channel):
        assert xml_parser.XPath(channel).first("title/text()") == "Mysterious Universe"

    def test_find_first_matching(self, channel):
        assert (
            xml_parser.XPath(channel).first("editor/text()", "managingEditor/text()")
            == "sales@mysteriousuniverse.org (8th Kind)"
        )

    def test_default(self, channel):
        assert (
            xml_parser.XPath(channel).first(
                "editor/text()", "managingEditor2/text()", default="unknown"
            )
            == "unknown"
        )
