from datetime import timedelta

import pytest
import requests

from django.core.exceptions import ValidationError
from django.utils import timezone

from jcasts.podcasts import websub
from jcasts.podcasts.factories import PodcastFactory
from jcasts.podcasts.models import Podcast


class TestVerifyIntent:
    challenge = "abc123"

    def test_denied(self, db, rf):
        podcast = PodcastFactory()
        req = rf.get(
            "/",
            {
                "hub.mode": "denied",
                "hub.challenge": self.challenge,
                "hub.topic": podcast.rss,
            },
        )
        challenge, status, subscribed = websub.verify_intent(req, podcast)
        assert challenge == self.challenge
        assert status == Podcast.SubscribeStatus.DENIED
        assert subscribed is None

    def test_unsubscribe(self, db, rf):
        podcast = PodcastFactory()
        req = rf.get(
            "/",
            {
                "hub.mode": "unsubscribe",
                "hub.challenge": self.challenge,
                "hub.topic": podcast.rss,
            },
        )
        challenge, status, subscribed = websub.verify_intent(req, podcast)
        assert challenge == self.challenge
        assert status == Podcast.SubscribeStatus.UNSUBSCRIBED
        assert subscribed is None

    def test_subscribe(self, db, rf):
        podcast = PodcastFactory()
        req = rf.get(
            "/",
            {
                "hub.mode": "subscribe",
                "hub.lease_seconds": "5000",
                "hub.challenge": self.challenge,
                "hub.topic": podcast.rss,
            },
        )
        challenge, status, subscribed = websub.verify_intent(req, podcast)
        assert challenge == self.challenge
        assert status == Podcast.SubscribeStatus.SUBSCRIBED
        assert (subscribed - timezone.now()).total_seconds() == pytest.approx(5000)

    def test_missing_challenge(self, db, rf):
        podcast = PodcastFactory()
        req = rf.get("/", {"hub.mode": "unsubscribe", "hub.topic": podcast.rss})
        with pytest.raises(ValidationError):
            websub.verify_intent(req, podcast)

    def test_invalid_mode(self, db, rf):
        podcast = PodcastFactory()
        req = rf.get(
            "/",
            {
                "hub.mode": "unknown",
                "hub.challenge": self.challenge,
                "hub.topic": podcast.rss,
            },
        )
        with pytest.raises(ValidationError):
            websub.verify_intent(req, podcast)

    def test_invalid_topic(self, db, rf):
        podcast = PodcastFactory()
        req = rf.get(
            "/",
            {
                "hub.mode": "unsubscribe",
                "hub.challenge": self.challenge,
                "hub.topic": "https//some-random.com",
            },
        )
        with pytest.raises(ValidationError):
            websub.verify_intent(req, podcast)

    def test_missing_lease_seconds(self, db, rf):
        podcast = PodcastFactory()
        req = rf.get(
            "/",
            {
                "hub.mode": "subscribe",
                "hub.challenge": self.challenge,
                "hub.topic": podcast.rss,
            },
        )
        with pytest.raises(ValidationError):
            websub.verify_intent(req, podcast)

    def test_invalid_lease_seconds(self, db, rf):
        podcast = PodcastFactory()
        req = rf.get(
            "/",
            {
                "hub.mode": "subscribe",
                "hub.lease_seconds": "xxx",
                "hub.challenge": self.challenge,
                "hub.topic": podcast.rss,
            },
        )
        with pytest.raises(ValidationError):
            websub.verify_intent(req, podcast)


class TestHandleUpdate:
    secret = "AAABBBCCC"

    def test_ok(self, db, rf, mock_parse_podcast_feed):
        podcast = PodcastFactory(
            subscribe_status=Podcast.SubscribeStatus.SUBSCRIBED,
            subscribe_secret=self.secret,
        )
        websub.handle_content_distribution(self.get_request(rf, self.secret), podcast)
        mock_parse_podcast_feed.assert_called_with(podcast.id, b"some-xml")

    def test_invalid_status(self, db, rf, mock_parse_podcast_feed):
        podcast = PodcastFactory(
            subscribe_status=Podcast.SubscribeStatus.UNSUBSCRIBED,
            subscribe_secret=self.secret,
        )
        with pytest.raises(ValidationError):
            websub.handle_content_distribution(
                self.get_request(rf, self.secret), podcast
            )
        mock_parse_podcast_feed.assert_not_called()

    def test_invalid_sig_method(self, db, rf, mock_parse_podcast_feed):
        podcast = PodcastFactory(
            subscribe_status=Podcast.SubscribeStatus.SUBSCRIBED,
            subscribe_secret=self.secret,
        )
        with pytest.raises(ValidationError):
            websub.handle_content_distribution(
                self.get_request(rf, self.secret, "sha1"), podcast
            )
        mock_parse_podcast_feed.assert_not_called()

    def test_invalid_sig_value(self, db, rf, mock_parse_podcast_feed):
        podcast = PodcastFactory(
            subscribe_status=Podcast.SubscribeStatus.SUBSCRIBED,
            subscribe_secret=self.secret,
        )
        with pytest.raises(ValidationError):
            websub.handle_content_distribution(self.get_request(rf, "BBBCCCC"), podcast)
        mock_parse_podcast_feed.assert_not_called()

    def test_missing_signature(self, db, rf, mock_parse_podcast_feed):

        podcast = PodcastFactory(
            subscribe_status=Podcast.SubscribeStatus.SUBSCRIBED,
            subscribe_secret=self.secret,
        )
        with pytest.raises(ValidationError):
            websub.handle_content_distribution(rf.post("/"), podcast)

    def get_request(self, rf, secret, method="sha512"):
        return rf.post(
            "/",
            data=b"some-xml",
            content_type="application/xml",
            HTTP_X_HUB_SIGNATURE=f"{method}={websub.create_hexdigest(secret)}",
        )


class TestCreateHexdigest:
    secret = "AAABBBCCC"

    def test_create(self):
        assert websub.create_hexdigest(self.secret) != self.secret


class TestMatchesSignature:
    secret = "AAABBBCCC"

    def test_matches(self):
        assert websub.matches_signature(
            self.secret, websub.create_hexdigest(self.secret)
        )

    def test_not_matches(self):
        assert not websub.matches_signature(
            self.secret, websub.create_hexdigest("DDDDEEEEFFF")
        )


class TestSubscribePodcasts:
    def test_subscribe(self, db, mocker):
        mock_subscribe = mocker.patch("jcasts.podcasts.websub.subscribe.delay")
        PodcastFactory(hub="https://example.com")
        websub.subscribe_podcasts()
        mock_subscribe.assert_called()


class TestSubscribe:

    hub = "https://pubsubhubbub.appspot.com/"

    def test_subscribe(self, db, mocker):
        mock_post = mocker.patch("requests.post")
        podcast = PodcastFactory(hub=self.hub)
        websub.subscribe(podcast.id)

        mock_post.assert_called()

        podcast.refresh_from_db()

        assert podcast.subscribe_status == Podcast.SubscribeStatus.REQUESTED
        assert podcast.subscribe_requested
        assert podcast.subscribe_secret
        assert not podcast.hub_exception

    def test_not_found(self, db, mocker):
        mock_post = mocker.patch("requests.post")
        websub.subscribe(1234)

        mock_post.assert_not_called()

    def test_failed(self, db, mocker):
        class MockResponse:
            def raise_for_status(self):
                raise requests.HTTPError()

        mock_post = mocker.patch("requests.post", return_value=MockResponse())

        podcast = PodcastFactory(hub=self.hub)
        websub.subscribe(podcast.id)

        mock_post.assert_called()

        podcast.refresh_from_db()

        assert podcast.subscribe_status == Podcast.SubscribeStatus.ERROR
        assert podcast.subscribe_requested is None
        assert podcast.subscribe_secret is None


class TestGetSubscribablePodcasts:
    hub = "https://pubsubhubbub.appspot.com/"

    @pytest.mark.parametrize(
        "hub,active,status,subscribed,exists",
        [
            (None, True, Podcast.SubscribeStatus.UNSUBSCRIBED, None, False),
            (hub, True, Podcast.SubscribeStatus.UNSUBSCRIBED, None, True),
            (hub, False, Podcast.SubscribeStatus.UNSUBSCRIBED, None, False),
            (hub, True, Podcast.SubscribeStatus.REQUESTED, None, False),
            (
                hub,
                True,
                Podcast.SubscribeStatus.SUBSCRIBED,
                timedelta(days=-90),
                True,
            ),
            (
                hub,
                True,
                Podcast.SubscribeStatus.SUBSCRIBED,
                timedelta(days=30),
                False,
            ),
        ],
    )
    def test_get_podcasts(self, db, hub, active, status, subscribed, exists):

        PodcastFactory(
            hub=hub,
            active=active,
            subscribe_status=status,
            subscribed=timezone.now() + subscribed if subscribed else None,
        )
        assert websub.get_subscribable_podcasts().exists() is exists
