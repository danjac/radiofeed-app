from __future__ import annotations

import dataclasses
import hmac
import http
import uuid

from datetime import timedelta

import pytest
import requests

from django.utils import timezone

from radiofeed.podcasts import subscriber
from radiofeed.podcasts.factories import create_podcast


@dataclasses.dataclass
class MockResponse:
    status_code: int

    def raise_for_status(self):
        if self.status_code not in range(200, 400):
            raise requests.HTTPError("oops")


class TestGetPodcastsForSubscribe:
    hub = "https://example.com/"

    def test_not_websub(self, db, podcast):
        assert subscriber.get_podcasts_for_subscribe().count() == 0

    def test_expired_none(self, db):
        create_podcast(
            websub_hub=self.hub, websub_expires=None, websub_mode="subscribe"
        )
        assert subscriber.get_podcasts_for_subscribe().count() == 0

    def test_expired(self, db):
        create_podcast(
            websub_hub=self.hub,
            websub_expires=timezone.now() - timedelta(days=1),
            websub_mode="subscribe",
        )

        assert subscriber.get_podcasts_for_subscribe().count() == 1

    def test_too_many_errors(self, db):
        create_podcast(
            websub_hub=self.hub,
            websub_expires=timezone.now() - timedelta(days=1),
            websub_mode="subscribe",
            num_websub_retries=3,
        )

        assert subscriber.get_podcasts_for_subscribe().count() == 0

    def test_expired_not_subscribed(self, db):
        create_podcast(
            websub_hub=self.hub,
            websub_expires=timezone.now() - timedelta(days=1),
            websub_mode="unsubscribe",
        )

        assert subscriber.get_podcasts_for_subscribe().count() == 0

    def test_not_expired(self, db):
        create_podcast(
            websub_hub=self.hub,
            websub_expires=timezone.now() + timedelta(days=1),
            websub_mode="subscribe",
        )

        assert subscriber.get_podcasts_for_subscribe().count() == 0


class TestCheckSignature:
    body = b"testme"
    content_type = "application/xml"

    @pytest.fixture
    def podcast(self, db):
        return create_podcast(websub_secret=uuid.uuid4())

    def test_ok(self, rf, podcast):
        sig = hmac.new(
            podcast.websub_secret.hex.encode("utf-8"), self.body, "sha1"
        ).hexdigest()

        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert subscriber.check_signature(req, podcast)

    def test_signature_mismatch(self, rf, podcast):
        sig = hmac.new(uuid.uuid4().hex.encode("utf-8"), self.body, "sha1").hexdigest()

        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert not subscriber.check_signature(req, podcast)

    def test_content_length_too_large(self, rf, podcast):
        sig = hmac.new(
            podcast.websub_secret.hex.encode("utf-8"), self.body, "sha1"
        ).hexdigest()

        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            CONTENT_LENGTH=2000000000,
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert not subscriber.check_signature(req, podcast)

    def test_hub_signature_header_missing(self, rf, podcast):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
        )

        assert not subscriber.check_signature(req, podcast)

    def test_invalid_algo(self, rf, podcast):
        sig = hmac.new(
            podcast.websub_secret.hex.encode("utf-8"), self.body, "sha1"
        ).hexdigest()

        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1111={sig}",
        )

        assert not subscriber.check_signature(req, podcast)


class TestSubscribe:
    def test_accepted(self, mocker, podcast):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        subscriber.subscribe(podcast)

        podcast.refresh_from_db()

        assert podcast.websub_mode == "subscribe"
        assert podcast.websub_expires
        assert podcast.websub_secret

    def test_unsubscribe(self, mocker, podcast):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        subscriber.subscribe(podcast, mode="unsubscribe")

        podcast.refresh_from_db()

        assert podcast.websub_mode == "unsubscribe"
        assert podcast.websub_expires is None
        assert podcast.websub_secret

    def test_error(self, mocker, podcast):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.NOT_FOUND),
        )

        with pytest.raises(requests.HTTPError):
            subscriber.subscribe(podcast)

        podcast.refresh_from_db()

        assert podcast.websub_mode == ""
        assert podcast.websub_expires is None
        assert podcast.websub_secret is None

        assert podcast.num_websub_retries == 1
