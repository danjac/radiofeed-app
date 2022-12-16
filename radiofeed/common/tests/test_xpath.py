from __future__ import annotations

import pathlib

import pytest

from radiofeed.common.xpath import XPathFinder


class TestXPathFinder:
    def read_mock_file(self, mock_filename="rss_mock.xml"):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()

    @pytest.fixture
    def channel(self):
        return next(XPathFinder().iterparse(self.read_mock_file(), "channel"))

    def test_iter(self, channel):
        assert list(XPathFinder().iter(channel, "title/text()")) == [
            "Mysterious Universe"
        ]

    def test_aslist(self, channel):
        assert XPathFinder().aslist(channel, "title/text()") == ["Mysterious Universe"]

    def test_asdict(self, channel):

        assert XPathFinder(
            {
                "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
            }
        ).asdict(
            channel,
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
        assert XPathFinder().first(channel, "title/text()") == "Mysterious Universe"

    def test_find_first_matching(self, channel):
        assert (
            XPathFinder().first(channel, "editor/text()", "managingEditor/text()")
            == "sales@mysteriousuniverse.org (8th Kind)"
        )

    def test_default(self, channel):
        assert (
            XPathFinder().first(channel, "editor/text()", "managingEditor2/text()")
            is None
        )
