import pathlib

import pytest

from radiofeed.xml_parser import XMLParser


class TestXMLParser:
    def read_mock_file(self, mock_filename="rss_mock.xml"):
        return (pathlib.Path(__file__).parent / "mocks" / mock_filename).read_bytes()

    @pytest.fixture()
    def channel(self):
        return next(XMLParser().iterparse(self.read_mock_file(), "rss", "channel"))

    def test_itertext(self, channel):
        assert list(XMLParser().itertext(channel, "title/text()")) == [
            "Mysterious Universe"
        ]

    def test_aslist(self, channel):
        assert XMLParser().aslist(channel, "title/text()") == ["Mysterious Universe"]

    def test_asdict(self, channel):
        assert XMLParser(
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
        assert XMLParser().first(channel, "title/text()") == "Mysterious Universe"

    def test_find_first_matching(self, channel):
        assert (
            XMLParser().first(channel, "editor/text()", "managingEditor/text()")
            == "sales@mysteriousuniverse.org (8th Kind)"
        )

    def test_default(self, channel):
        assert (
            XMLParser().first(channel, "editor/text()", "managingEditor2/text()")
            is None
        )
