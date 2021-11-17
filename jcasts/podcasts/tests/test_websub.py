from datetime import timedelta

import pytest
import requests

from django.utils import timezone

from jcasts.podcasts import websub
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast


class TestSubscribe:
    hub = "https://simplecast.superfeedr.com/"
    url = "https://simplecast.superfeedr.com/r/1234"

    def test_request_ok(self, db, mocker):
        mock_post = mocker.patch("requests.post")

        podcast = PodcastFactory(
            websub_hub=self.hub,
            websub_url=self.url,
            websub_status=Podcast.WebSubStatus.PENDING,
        )

        result = websub.subscribe(podcast.id)

        assert result.podcast_id == podcast.id
        assert result.status == Podcast.WebSubStatus.REQUESTED
        assert result.exception is None

        mock_post.assert_called()

        podcast.refresh_from_db()

        assert podcast.websub_token
        assert podcast.websub_status == Podcast.WebSubStatus.REQUESTED
        assert podcast.websub_status_changed

    def test_request_failed(self, db, mocker):
        class MockResponse:
            content = b"failed"

            def raise_for_status(self):
                raise requests.RequestException(response=self)

        mock_post = mocker.patch("requests.post", return_value=MockResponse())

        podcast = PodcastFactory(
            websub_hub=self.hub,
            websub_url=self.url,
            websub_status=Podcast.WebSubStatus.PENDING,
        )

        result = websub.subscribe(podcast.id)

        assert result.podcast_id == podcast.id
        assert result.status == Podcast.WebSubStatus.INACTIVE
        assert result.exception

        mock_post.assert_called()

        podcast.refresh_from_db()

        assert podcast.websub_token is None
        assert podcast.websub_status == Podcast.WebSubStatus.INACTIVE
        assert podcast.websub_status_changed
        assert podcast.websub_exception

    def test_podcast_not_found(self, db, mocker):
        mock_post = mocker.patch("requests.post")

        result = websub.subscribe(1234)
        assert result.podcast_id == 1234
        assert result.exception

        mock_post.assert_not_called()


class TestEncodeToken:
    token = "abc123"
    method = "sha1"

    def test_encode(self):
        assert websub.encode_token(self.token) != self.token

    def test_compare_signature_true(self):
        encoded = websub.encode_token(self.token)
        assert websub.compare_signature(self.token, encoded, self.method)

    def test_compare_signature_false(self):
        encoded = websub.encode_token("some-random")
        assert not websub.compare_signature(self.token, encoded, self.method)

    def test_compare_signature_none(self):
        encoded = websub.encode_token(self.token)
        assert not websub.compare_signature(None, encoded, self.method)


class TestSubscribePodcasts:
    def test_subscribe(self, db, mocker):
        podcast = PodcastFactory(
            websub_hub="https://example.com/hub/",
            websub_url="https://example.com/hub/12334/",
            websub_status=Podcast.WebSubStatus.PENDING,
        )
        mock_subscribe = mocker.patch("jcasts.podcasts.websub.subscribe.delay")
        websub.subscribe_podcasts()

        mock_subscribe.assert_called_with(podcast.id)


class TestGetPodcastsForSubscripion:
    hub = "https://simplecast.superfeedr.com/"
    url = "https://simplecast.superfeedr.com/r/1234"

    @pytest.mark.parametrize(
        "active,hub,status,subscribed,changed,exists",
        [
            (True, hub, Podcast.WebSubStatus.PENDING, None, None, True),
            (True, None, Podcast.WebSubStatus.PENDING, None, None, False),
            (True, hub, Podcast.WebSubStatus.REQUESTED, None, None, False),
            (True, hub, Podcast.WebSubStatus.ACTIVE, timedelta(days=1), None, False),
            (True, hub, Podcast.WebSubStatus.ACTIVE, timedelta(days=-1), None, True),
            (True, hub, Podcast.WebSubStatus.REQUESTED, timedelta(days=1), None, False),
            (
                True,
                hub,
                Podcast.WebSubStatus.REQUESTED,
                timedelta(days=1),
                timedelta(seconds=60),
                False,
            ),
            (
                True,
                hub,
                Podcast.WebSubStatus.REQUESTED,
                timedelta(days=1),
                timedelta(seconds=7200),
                True,
            ),
            (False, hub, Podcast.WebSubStatus.PENDING, None, None, False),
        ],
    )
    def test_get_podcasts(self, db, active, hub, status, subscribed, changed, exists):
        now = timezone.now()

        PodcastFactory(
            active=active,
            websub_hub=hub,
            websub_status=status,
            websub_subscribed=now + subscribed if subscribed else None,
            websub_url=self.url,
            websub_status_changed=now - changed if changed else None,
        )

        assert websub.get_podcasts_for_subscription().exists() is exists
