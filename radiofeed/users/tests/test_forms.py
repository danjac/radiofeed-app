import pathlib

from django.core.files.uploadedfile import SimpleUploadedFile

from radiofeed.users.forms import OpmlUploadForm


class TestOpmlUploadForm:
    def test_parse_feeds(self):
        form = OpmlUploadForm()
        form.cleaned_data = {
            "opml": SimpleUploadedFile(
                "feeds.opml",
                (pathlib.Path(__file__).parent / "mocks" / "feeds.opml").read_bytes(),
                content_type="text/xml",
            )
        }

        assert len(list(form.parse_feeds())) == 11

    def test_parser_error(self):
        form = OpmlUploadForm()
        form.cleaned_data = {
            "opml": SimpleUploadedFile(
                "feeds.opml",
                b"",
                content_type="text/xml",
            )
        }
        assert len(list(form.parse_feeds())) == 0
