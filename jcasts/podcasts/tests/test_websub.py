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

    def test_not_subscribed(self, db):
        PodcastFactory(hub=self.hub)
        assert websub.get_podcasts().count() == 1

    def test_requested(self, db):
        PodcastFactory(hub=self.hub, requested=timezone.now())
        assert websub.get_podcasts().count() == 0

    def test_exception(self, db):
        PodcastFactory(hub=self.hub, hub_exception="broken")
        assert websub.get_podcasts().count() == 0

    def test_subscribed_out_of_date(self, db):
        PodcastFactory(hub=self.hub, subscribed=timezone.now() - timedelta(hours=1))
        assert websub.get_podcasts().count() == 1

    def test_hub_is_none(self, db):
        PodcastFactory(hub=None)
        assert websub.get_podcasts().count() == 0

    def test_subscribed_not_out_of_date(self, db):
        PodcastFactory(hub=self.hub, subscribed=timezone.now() + timedelta(hours=1))
        assert websub.get_podcasts().count() == 0


class TestSubscribe:
    mock_http_post = "requests.post"
    hub = "https://pubsubhubbub.appspot.com/"

    def test_ok(self, db, mocker):
        mock_post = mocker.patch(self.mock_http_post, return_value=MockResponse())

        podcast = PodcastFactory(hub=self.hub)
        websub.subscribe(podcast.id)
        mock_post.assert_called()

        podcast.refresh_from_db()
        assert podcast.hub_token
        assert podcast.requested

    def test_exception(self, db, mocker):
        mock_post = mocker.patch(self.mock_http_post, return_value=MockBadResponse())

        podcast = PodcastFactory(
            hub=self.hub, subscribed=timezone.now() - timedelta(hours=1)
        )
        websub.subscribe(podcast.id)
        mock_post.assert_called()

        podcast.refresh_from_db()
        assert podcast.hub_token is None
        assert podcast.subscribed is None
        assert podcast.requested is None
        assert podcast.hub_exception
