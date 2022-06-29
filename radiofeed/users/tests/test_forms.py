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

    def test_subscribe_to_feeds(self, mocker, form, user, podcast):
        mocker.patch(
            "radiofeed.users.forms.opml_parser.parse_opml",
            return_value=[
                Outline(rss=podcast.rss, title=""),
            ],
        )
        assert form.subscribe_to_feeds(user) == 1
        assert Subscription.objects.filter(user=user, podcast=podcast).count() == 1

    def test_subscribe_to_feeds_no_results(self, mocker, form, user, podcast):
        mocker.patch(
            "radiofeed.users.forms.opml_parser.parse_opml",
            return_value=[],
        )
        assert form.subscribe_to_feeds(user) == 0
        assert Subscription.objects.filter(user=user, podcast=podcast).count() == 0

    def test_subscribe_to_feeds_parser_error(self, mocker, form, user, podcast):
        mocker.patch(
            "radiofeed.users.forms.opml_parser.parse_opml",
            side_effect=opml_parser.OpmlParserError,
        )
        assert form.subscribe_to_feeds(user) == 0
        assert Subscription.objects.filter(user=user, podcast=podcast).count() == 0
