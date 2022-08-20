from __future__ import annotations

import pathlib

import pytest

from radiofeed.feedparser.xml_parser import XPathFinder, parse_xml, xpath_finder


class TestXPathFinder:
    def read_mock_file(self, mock_filename="rss_mock.xml"):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()

    @pytest.fixture
    def channel(self):
        return next(parse_xml(self.read_mock_file(), "channel"))

    def test_contexttmanager(self, channel):
        with xpath_finder(channel) as finder:
            assert finder.first("title/text()") == "Mysterious Universe"

    def test_iter(self, channel):
        assert list(XPathFinder(channel).iter("title/text()")) == [
            "Mysterious Universe"
        ]

    def test_to_list(self, channel):
        assert XPathFinder(channel).to_list("title/text()") == ["Mysterious Universe"]

    def test_to_dict(self, channel):

        assert XPathFinder(channel).to_dict(
            title="title/text()",
            cover_url=(
                "itunes:image/@href",
                "image/url/text()",
            ),
            # this path does not exist, should be None
            editor="managingEditor2/text()",
        ) == {
            "title": "Mysterious Universe",
            "cover_url": "https://mysteriousuniverse.org/wp-content/uploads/2018/11/itunes_14k.jpg",
            "editor": None,
        }

    def test_first_exists(self, channel):
        assert XPathFinder(channel).first("title/text()") == "Mysterious Universe"

    def test_find_first_matching(self, channel):
        assert (
            XPathFinder(channel).first("editor/text()", "managingEditor/text()")
            == "sales@mysteriousuniverse.org (8th Kind)"
        )

    def test_default(self, channel):
        assert (
            XPathFinder(channel).first("editor/text()", "managingEditor2/text()")
            is None
        )
