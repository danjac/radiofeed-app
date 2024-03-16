import io
import pathlib

from radiofeed.feedparser.opml_parser import parse_opml


class TestParseOpml:
    def test_parse_ok(self):
        with (pathlib.Path(__file__).parent / "mocks" / "feeds.opml").open("rb") as fp:
            feeds = list(parse_opml(fp))
        assert len(feeds) == 11

    def test_parse_empty(self):
        feeds = list(parse_opml(io.BytesIO(b"")))

        assert len(feeds) == 0
