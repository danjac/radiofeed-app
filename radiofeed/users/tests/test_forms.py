import pathlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from radiofeed.podcasts.models import Subscription
from radiofeed.podcasts.tests.factories import create_podcast
from radiofeed.users.forms import OpmlUploadForm


class TestOpmlUploadForm:
    @pytest.fixture()
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

    @pytest.fixture()
    def podcast(self):
        return create_podcast(
            rss="https://feeds.99percentinvisible.org/99percentinvisible"
        )

    @pytest.mark.django_db()
    def test_subscribe_to_feeds(self, form, user, podcast):
        subscription = form.subscribe_to_feeds(user)[0]

        assert subscription.podcast == podcast
        assert subscription.subscriber == user

        assert (
            Subscription.objects.filter(subscriber=user, podcast=podcast).count() == 1
        )

    @pytest.mark.django_db()
    def test_subscribe_to_feeds_parser_error(self, user, podcast):
        form = OpmlUploadForm()
        form.cleaned_data = {
            "opml": SimpleUploadedFile("feeds.opml", b"", content_type="text/xml")
        }
        assert form.subscribe_to_feeds(user) == []
        assert (
            Subscription.objects.filter(subscriber=user, podcast=podcast).count() == 0
        )
