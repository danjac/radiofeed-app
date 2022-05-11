from django.core.files.uploadedfile import SimpleUploadedFile

from radiofeed.podcasts.parsers import opml_parser
from radiofeed.users.forms import OpmlUploadForm


class TestOpmlUploadForm:
    def test_parse_opml_feed(self, mocker):
        form = OpmlUploadForm()
        form.cleaned_data = {
            "opml": SimpleUploadedFile(
                "feeds.opml", b"content", content_type="text/xml"
            )
        }
        mocker.patch(
            "radiofeed.users.forms.opml_parser.parse_opml",
            return_value=[
                opml_parser.Outline(rss="https://example.com/test.xml"),
                opml_parser.Outline(rss=None),
            ],
        )
        assert form.parse_opml_feeds() == ["https://example.com/test.xml"]
