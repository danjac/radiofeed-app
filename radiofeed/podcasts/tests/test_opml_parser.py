import pathlib

<<<<<<<< HEAD:radiofeed/podcasts/tests/test_opml_parser.py
<<<<<<<< HEAD:radiofeed/podcasts/tests/test_opml_parser.py
from radiofeed.podcasts.opml_parser import parse_opml
========
from radiofeed.parsers.opml_parser import parse_opml
>>>>>>>> f7f200b02 (refactor: reorganise parsers):radiofeed/parsers/tests/test_opml_parser.py
========
from radiofeed.podcasts.parsers.opml_parser import parse_opml
>>>>>>>> f991ea3c0 (refactor: move parsers package to podcasts):radiofeed/podcasts/parsers/tests/test_opml_parser.py


class TestParseOpml:
    def test_parse_ok(self):
        path = pathlib.Path(__file__).parent / "mocks" / "feeds.opml"
        feeds = list(parse_opml(path.read_bytes()))
        assert len(feeds) == 11

    def test_parse_empty(self):
        feeds = list(parse_opml(b""))

        assert len(feeds) == 0
