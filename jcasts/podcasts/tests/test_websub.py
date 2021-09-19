import http

from datetime import timedelta

import requests

from django.utils import timezone

from jcasts.podcasts import websub
from jcasts.podcasts.factories import PodcastFactory


class MockResponse:
    def __init__(
        self,
        url="",
        status=http.HTTPStatus.OK,
        content=b"",
        headers=None,
        links=None,
    ):
        self.url = url
        self.content = content
        self.headers = headers or {}
        self.links = links or {}
        self.status_code = status

    def raise_for_status(self):
        ...


class MockBadResponse(MockResponse):
    def raise_for_status(self):
        raise requests.HTTPError()


class TestGetPodcasts:
    hub = "https://pubsubhubbub.appspot.com/"

    def test_not_websub_subscribed(self, db):
        PodcastFactory(websub_hub=self.hub)
        assert websub.get_podcasts().count() == 1

    def test_websub_requested(self, db):
        PodcastFactory(websub_hub=self.hub, websub_requested=timezone.now())
        assert websub.get_podcasts().count() == 0

    def test_exception(self, db):
        PodcastFactory(websub_hub=self.hub, websub_exception="broken")
        assert websub.get_podcasts().count() == 0

    def test_websub_subscribed_out_of_date(self, db):
        PodcastFactory(
            websub_hub=self.hub, websub_subscribed=timezone.now() - timedelta(hours=1)
        )
        assert websub.get_podcasts().count() == 1

    def test_websub_hub_is_none(self, db):
        PodcastFactory(websub_hub=None)
        assert websub.get_podcasts().count() == 0

    def test_websub_subscribed_not_out_of_date(self, db):
        PodcastFactory(
            websub_hub=self.hub, websub_subscribed=timezone.now() + timedelta(hours=1)
        )
        assert websub.get_podcasts().count() == 0


class TestSubscribe:
    mock_http_post = "requests.post"
    hub = "https://pubsubhubbub.appspot.com/"

    def test_ok(self, db, mocker):
        mock_post = mocker.patch(self.mock_http_post, return_value=MockResponse())

        podcast = PodcastFactory(websub_hub=self.hub)
        websub.subscribe(podcast.id)
        mock_post.assert_called()

        podcast.refresh_from_db()
        assert podcast.websub_token
        assert podcast.websub_requested
        assert not podcast.websub_exception

    def test_exception(self, db, mocker):
        mock_post = mocker.patch(self.mock_http_post, return_value=MockBadResponse())

        podcast = PodcastFactory(
            websub_hub=self.hub, websub_subscribed=timezone.now() - timedelta(hours=1)
        )
        websub.subscribe(podcast.id)
        mock_post.assert_called()

        podcast.refresh_from_db()
        assert podcast.websub_token is None
        assert podcast.websub_subscribed is None
        assert podcast.websub_requested is None
        assert podcast.websub_exception
