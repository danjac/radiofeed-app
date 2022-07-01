import pathlib

import pytest

from radiofeed.common.utils.xml import XPathFinder, parse_xml


class TestXPath:
    def read_mock_file(self, mock_filename="rss_mock.xml"):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()

    @pytest.fixture
    def channel(self):
        return next(parse_xml(self.read_mock_file(), "channel"))

    def test_iter(self, channel):
        assert list(XPathFinder(channel).iter("title/text()")) == [
            "Mysterious Universe"
        ]

    def test_first_exists(self, channel):
        assert XPathFinder(channel).first("title/text()") == "Mysterious Universe"

    def test_find_first_matching(self, channel):
        assert (
            XPathFinder(channel).first("editor/text()", "managingEditor/text()")
            == "sales@mysteriousuniverse.org (8th Kind)"
        )

    def test_default(self, channel):
        assert (
            XPathFinder(channel).first(
                "editor/text()", "managingEditor2/text()", default="unknown"
            )
            == "unknown"
        )
