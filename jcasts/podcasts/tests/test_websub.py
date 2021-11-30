import uuid

from datetime import timedelta

import pytest
import requests

from django.utils import timezone

from jcasts.podcasts import websub
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast


class TestCheckSignature:
    def test_ok(self, rf):

        secret = uuid.uuid4()
        body = b"testing"

        sig = websub.make_signature(secret, body, "sha1")

        req = rf.post(
            "/",
            data=body,
            content_type="application/xml",
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert websub.check_signature(req, secret)

    def test_invalid_secret(self, rf):

        secret = uuid.uuid4()
        body = b"testing"
        sig = websub.make_signature(secret, body, "sha1")

        req = rf.post(
            "/",
            data=body,
            content_type="application/xml",
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert not websub.check_signature(req, uuid.uuid4())

    def test_missing_sig(self, rf):

        secret = uuid.uuid4()

        req = rf.post(
            "/",
            data=b"testing",
            content_type="application/xml",
        )

        assert not websub.check_signature(req, secret)


class TestSubscribePodcasts:
    hub = "https://amazinglybrilliant.superfeedr.com/"
    url = "https://podnews.net/rss"

    @pytest.fixture
    def mock_subscribe(self, mocker):
        return mocker.patch("jcasts.podcasts.websub.subscribe.delay")

    def test_no_hub(self, db, mock_subscribe):
        PodcastFactory(websub_url=self.url, websub_hub=None)
        websub.subscribe_podcasts()
        mock_subscribe.assert_not_called()

    def test_no_status(self, db, mock_subscribe):
        podcast = PodcastFactory(websub_url=self.url, websub_hub=self.hub)
        websub.subscribe_podcasts()
        mock_subscribe.assert_called_with(podcast.id)

    def test_active_timed_out(self, db, mock_subscribe):
        podcast = PodcastFactory(
            websub_url=self.url,
            websub_hub=self.hub,
            websub_status=Podcast.WebSubStatus.ACTIVE,
            websub_timeout=timezone.now() - timedelta(days=3),
        )
        websub.subscribe_podcasts()
        mock_subscribe.assert_called_with(podcast.id)

    def test_inactive(self, db, mock_subscribe):
        PodcastFactory(websub_url=self.url, websub_hub=self.hub, active=False)
        websub.subscribe_podcasts()
        mock_subscribe.assert_not_called()

    def test_already_requested(self, db, mock_subscribe):
        PodcastFactory(
            websub_url=self.url,
            websub_hub=self.hub,
            websub_status=Podcast.WebSubStatus.REQUESTED,
        )
        websub.subscribe_podcasts()
        mock_subscribe.assert_not_called()


class TestSubscribe:
    hub = "https://amazinglybrilliant.superfeedr.com/"
    url = "https://podnews.net/rss"

    def test_subscribe(self, db, mocker):
        mock_post = mocker.patch("requests.post")
        podcast = PodcastFactory(websub_url=self.url, websub_hub=self.hub)

        websub.subscribe(podcast.id)

        mock_post.assert_called()

        podcast.refresh_from_db()

        assert podcast.websub_secret
        assert podcast.websub_mode == "subscribe"
        assert podcast.websub_status == Podcast.WebSubStatus.REQUESTED
        assert podcast.websub_status_changed
        assert not podcast.websub_exception

    def test_already_requested(self, db, mocker):
        mock_post = mocker.patch("requests.post")
        podcast = PodcastFactory(
            websub_url=self.url,
            websub_hub=self.hub,
            websub_status=Podcast.WebSubStatus.REQUESTED,
        )

        websub.subscribe(podcast.id)

        mock_post.not_assert_called()

    def test_subscribe_error(self, db, mocker):
        class BadResponse:
            content = b"oops"

            def raise_for_status(self):
                raise requests.HTTPError()

        mock_post = mocker.patch("requests.post", return_value=BadResponse())
        podcast = PodcastFactory(websub_url=self.url, websub_hub=self.hub)

        websub.subscribe(podcast.id)

        mock_post.assert_called()

        podcast.refresh_from_db()

        assert podcast.websub_secret
        assert podcast.websub_mode == "subscribe"
        assert podcast.websub_status == Podcast.WebSubStatus.ERROR
        assert podcast.websub_status_changed
        assert podcast.websub_exception
