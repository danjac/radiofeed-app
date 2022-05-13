import pytest

from django.core.files.uploadedfile import SimpleUploadedFile

from radiofeed.parsers import opml_parser
from radiofeed.users.forms import OpmlUploadForm


class TestOpmlUploadForm:
    @pytest.fixture
    def form(self):
        form = OpmlUploadForm()
        form.cleaned_data = {
            "opml": SimpleUploadedFile(
                "feeds.opml", b"content", content_type="text/xml"
            )
        }
        return form

    def test_parse_opml_feed(self, mocker, form):
        mocker.patch(
            "radiofeed.users.forms.opml_parser.parse_opml",
            return_value=[
                opml_parser.Outline(rss="https://example.com/test.xml"),
                opml_parser.Outline(rss=None),
            ],
        )
        assert form.parse_opml_feeds() == ["https://example.com/test.xml"]

    def test_parse_opml_feed_error(self, mocker, form):
        mocker.patch(
            "radiofeed.users.forms.opml_parser.parse_opml",
            side_effect=opml_parser.OpmlParserError,
        )
        assert form.parse_opml_feeds() == []
