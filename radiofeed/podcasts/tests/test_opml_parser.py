import pathlib

from radiofeed.podcasts.opml_parser import parse_opml


class TestParseOpml:
    def test_parse_ok(self):
        path = pathlib.Path(__file__).parent / "mocks" / "feeds.opml"
        feeds = list(parse_opml(path.read_bytes()))
        assert len(feeds) == 11

    def test_parse_empty(self):
        feeds = list(parse_opml(b""))

        assert len(feeds) == 0
