import pytest

from django.core.files.uploadedfile import SimpleUploadedFile

from radiofeed.podcasts.models import Subscription
from radiofeed.podcasts.parsers import opml_parser
from radiofeed.podcasts.parsers.opml_parser import Outline
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

    def test_create_subscriptions(self, mocker, form, user, podcast):
        mocker.patch(
            "radiofeed.users.forms.opml_parser.parse_opml",
            return_value=[
                Outline(rss=podcast.rss, title=""),
            ],
        )
        assert form.create_subscriptions(user) == 1
        assert Subscription.objects.filter(user=user, podcast=podcast).count() == 1

    def test_parse_opml_feed(self, mocker, form):
        mocker.patch(
            "radiofeed.users.forms.opml_parser.parse_opml",
            return_value=[
                Outline(rss="https://example.com/test.xml", title=""),
            ],
        )
        assert list(form.parse_opml_feeds(300)) == ["https://example.com/test.xml"]

    def test_parse_opml_feed_error(self, mocker, form):
        mocker.patch(
            "radiofeed.users.forms.opml_parser.parse_opml",
            side_effect=opml_parser.OpmlParserError,
        )
        assert list(form.parse_opml_feeds(300)) == []
