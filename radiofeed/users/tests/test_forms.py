import pathlib

import lxml
import pytest

from django.core.files.uploadedfile import SimpleUploadedFile

from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.models import Subscription
from radiofeed.users.forms import OpmlUploadForm


class TestOpmlUploadForm:
    @pytest.fixture
    def form(self):
        form = OpmlUploadForm()
        form.cleaned_data = {
            "opml": SimpleUploadedFile(
                "feeds.opml",
                (pathlib.Path(__file__).parent / "mocks" / "feeds.opml").read_bytes(),
                content_type="text/xml",
            )
        }
        return form

    @pytest.fixture
    def podcast(self, db):
        return PodcastFactory(
            rss="https://feeds.99percentinvisible.org/99percentinvisible"
        )

    def test_subscribe_to_feeds(self, form, user, podcast):
        assert form.subscribe_to_feeds(user) == 1
        assert Subscription.objects.filter(user=user, podcast=podcast).count() == 1

    def test_subscribe_to_feeds_parser_error(self, user, podcast, mocker):
        mocker.patch(
            "radiofeed.common.utils.xml.parse_xml",
            side_effect=lxml.etree.XMLSyntaxError,
        )

        form = OpmlUploadForm()
        form.cleaned_data = {
            "opml": SimpleUploadedFile(
                "feeds.opml", b"content", content_type="text/xml"
            )
        }
        assert form.subscribe_to_feeds(user) == 0
        assert Subscription.objects.filter(user=user, podcast=podcast).count() == 0
