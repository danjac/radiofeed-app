import http
import uuid

from datetime import timedelta

import faker
import pytest
import requests

from django.utils import timezone

from jcasts.podcasts import websub
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast


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


class TestCheckSignature:
    @pytest.fixture
    def req_body(self):
        yield faker.Faker().name().encode("utf-8")

    def make_sig_header(self, body, secret, algo="sha512"):
        return f"{algo}={websub.make_hex_digest(algo, body, secret)}"

    def test_secret_is_none(self, rf):
        websub.check_signature(rf.post("/"), Podcast())

    def test_ok(self, rf, req_body):
        podcast = Podcast(websub_secret=uuid.uuid4())
        req = rf.post(
            "/",
            req_body,
            content_type="text/xml",
            HTTP_X_HUB_SIGNATURE=self.make_sig_header(req_body, podcast.websub_secret),
        )
        websub.check_signature(req, podcast)

    def test_sig_header_missing(self, rf, req_body):
        podcast = Podcast(websub_secret=uuid.uuid4())
        req = rf.post(
            "/",
            req_body,
            content_type="text/xml",
        )
        with pytest.raises(websub.InvalidSignature):
            websub.check_signature(req, podcast)

    def test_body_too_large(self, rf, req_body):
        podcast = Podcast(websub_secret=uuid.uuid4())
        body = req_body * 30000000

        req = rf.post(
            "/",
            body,
            content_type="text/xml",
            HTTP_X_HUB_SIGNATURE=self.make_sig_header(req_body, podcast.websub_secret),
        )
        with pytest.raises(websub.InvalidSignature):
            websub.check_signature(req, podcast)

    def test_invalid_algo(self, rf, req_body):
        podcast = Podcast(websub_secret=uuid.uuid4())
        sig = self.make_sig_header(req_body, podcast.websub_secret).split("=")[1]
        req = rf.post(
            "/",
            req_body,
            content_type="text/xml",
            HTTP_X_HUB_SIGNATURE=f"bad-algo={sig}",
        )
        with pytest.raises(websub.InvalidSignature):
            websub.check_signature(req, podcast)

    def test_signature_mismatch(self, rf, req_body):
        podcast = Podcast(websub_secret=uuid.uuid4())
        req = rf.post(
            "/",
            req_body,
            content_type="text/xml",
            HTTP_X_HUB_SIGNATURE=self.make_sig_header(req_body, uuid.uuid4()),
        )
        with pytest.raises(websub.InvalidSignature):
            websub.check_signature(req, podcast)


class TestSubscribePodcasts:
    hub = "https://pubsubhubbub.appspot.com/"

    def test_ok(self, db, mocker):
        PodcastFactory.create_batch(
            3, websub_hub=self.hub, websub_subscribed=timezone.now()
        )
        mock_subscribe = mocker.patch("jcasts.podcasts.websub.subscribe.delay")
        assert websub.subscribe_podcasts() == 3
        mock_subscribe.assert_called()


class TestGetPodcasts:
    hub = "https://pubsubhubbub.appspot.com/"

    def test_not_websub_subscribed(self, db):
        PodcastFactory(websub_hub=self.hub)
        assert websub.get_podcasts().count() == 1

    def test_has_exception(self, db):
        PodcastFactory(websub_hub=self.hub, websub_exception="broken")
        assert websub.get_podcasts().count() == 0

    def test_has_exception_reverify(self, db):
        PodcastFactory(websub_hub=self.hub, websub_exception="broken")
        assert websub.get_podcasts(reverify=True).count() == 1

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
        assert podcast.websub_secret
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
        assert podcast.websub_secret is None
        assert podcast.websub_subscribed is None
        assert podcast.websub_requested is None
        assert podcast.websub_exception
