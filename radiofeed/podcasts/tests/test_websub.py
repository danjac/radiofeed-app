from __future__ import annotations

import dataclasses
import hmac
import http
import uuid
from datetime import timedelta

import pytest
import requests
from django.utils import timezone
from requests.exceptions import ReadTimeout

from radiofeed.podcasts import websub
from radiofeed.podcasts.factories import create_podcast

_WEBSUB_HUB = "https://example.com/"
_WEBSUB_TOPIC = "https://example.com/rss/"


@dataclasses.dataclass
class MockResponse:
    status_code: int

    def raise_for_status(self):
        if self.status_code not in range(200, 400):
            raise requests.HTTPError("oops")


class TestGetPodcastsForSubscribe:
    @pytest.mark.django_db
    def test_not_websub(self, db, podcast):
        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_not_subscribed(self, db):
        create_podcast(
            websub_hub=_WEBSUB_HUB,
            websub_topic=_WEBSUB_TOPIC,
            websub_expires=None,
            websub_mode="",
        )

        assert websub.get_podcasts_for_subscribe().count() == 1

    @pytest.mark.django_db
    def test_already_requested(self, db):
        create_podcast(
            websub_hub=_WEBSUB_HUB,
            websub_topic=_WEBSUB_TOPIC,
            websub_expires=None,
            websub_requested=timezone.now(),
            websub_mode="",
        )

        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_not_active(self, db):
        create_podcast(
            active=False,
            websub_hub=_WEBSUB_HUB,
            websub_topic=_WEBSUB_TOPIC,
            websub_expires=None,
            websub_mode="",
        )

        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_expired_none(self, db):
        create_podcast(
            websub_hub=_WEBSUB_HUB, websub_expires=None, websub_mode=websub.SUBSCRIBE
        )
        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_expired(self, db):
        create_podcast(
            websub_hub=_WEBSUB_HUB,
            websub_topic=_WEBSUB_TOPIC,
            websub_mode=websub.SUBSCRIBE,
            websub_expires=timezone.now() - timedelta(days=1),
        )

        assert websub.get_podcasts_for_subscribe().count() == 1

    @pytest.mark.django_db
    def test_expires_in_30_mins(self, db):
        create_podcast(
            websub_hub=_WEBSUB_HUB,
            websub_topic=_WEBSUB_TOPIC,
            websub_mode=websub.SUBSCRIBE,
            websub_expires=timezone.now() + timedelta(minutes=30),
        )

        assert websub.get_podcasts_for_subscribe().count() == 1

    @pytest.mark.django_db
    def test_expires_in_one_day(self, db):
        create_podcast(
            websub_hub=_WEBSUB_HUB,
            websub_topic=_WEBSUB_TOPIC,
            websub_mode=websub.SUBSCRIBE,
            websub_expires=timezone.now() + timedelta(days=1),
        )

        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_too_many_errors(self, db):
        create_podcast(
            websub_hub=_WEBSUB_HUB,
            websub_topic=_WEBSUB_TOPIC,
            websub_mode=websub.SUBSCRIBE,
            websub_expires=timezone.now() - timedelta(days=1),
            num_websub_retries=3,
        )

        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_expired_not_subscribed(self, db):
        create_podcast(
            websub_hub=_WEBSUB_HUB,
            websub_mode="unsubscribe",
            websub_expires=timezone.now() - timedelta(days=1),
        )

        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_not_expired(self, db):
        create_podcast(
            websub_hub=_WEBSUB_HUB,
            websub_mode=websub.SUBSCRIBE,
            websub_expires=timezone.now() + timedelta(days=1),
        )

        assert websub.get_podcasts_for_subscribe().count() == 0


class TestCheckSignature:
    body = b"testme"
    content_type = "application/xml"

    @pytest.fixture
    def secret(self):
        return uuid.uuid4()

    @pytest.fixture
    def signature(self, secret):
        return hmac.new(secret.hex.encode("utf-8"), self.body, "sha1").hexdigest()

    def test_ok(self, rf, secret, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        websub.check_signature(req, secret)

    def test_secret_is_none(self, rf, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        with pytest.raises(websub.InvalidSignature):
            websub.check_signature(req, None)

    def test_signature_mismatch(self, rf, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        with pytest.raises(websub.InvalidSignature):
            websub.check_signature(req, uuid.uuid4())

    def test_content_length_too_large(self, rf, secret, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            CONTENT_LENGTH=2000000000,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        with pytest.raises(websub.InvalidSignature):
            websub.check_signature(req, secret)

    def test_hub_signature_header_missing(self, rf, secret):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
        )

        with pytest.raises(websub.InvalidSignature):
            websub.check_signature(req, secret)

    def test_invalid_algo(self, rf, secret, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1111={signature}",
        )

        with pytest.raises(websub.InvalidSignature):
            websub.check_signature(req, secret)


class TestSubscribe:
    @pytest.fixture
    def websub_podcast(self):
        return create_podcast(websub_hub=_WEBSUB_HUB, websub_topic=_WEBSUB_TOPIC)

    @pytest.mark.django_db
    def test_accepted(self, mocker, websub_podcast):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        websub.subscribe(websub_podcast)

        websub_podcast.refresh_from_db()

        assert websub_podcast.websub_secret
        assert websub_podcast.websub_requested

    @pytest.mark.django_db
    def test_websub_hub_none(self, mocker):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        podcast = create_podcast()

        websub.subscribe(podcast)

        podcast.refresh_from_db()

        assert podcast.websub_secret is None
        assert podcast.websub_requested is None

    @pytest.mark.django_db
    def test_unsubscribe(self, mocker, websub_podcast):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        websub.subscribe(websub_podcast, mode="unsubscribe")

        websub_podcast.refresh_from_db()

        assert websub_podcast.websub_secret
        assert websub_podcast.websub_requested

    @pytest.mark.django_db
    def test_timeout(self, mocker, websub_podcast):
        mocker.patch(
            "requests.post",
            side_effect=ReadTimeout,
        )

        with pytest.raises(requests.ReadTimeout):
            websub.subscribe(websub_podcast)

        websub_podcast.refresh_from_db()

        assert websub_podcast.websub_secret is None
        assert websub_podcast.websub_requested is None
        assert websub_podcast.num_websub_retries == 1

    @pytest.mark.django_db
    def test_error(self, mocker, websub_podcast):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.NOT_FOUND),
        )

        with pytest.raises(requests.HTTPError):
            websub.subscribe(websub_podcast)

        websub_podcast.refresh_from_db()

        assert websub_podcast.websub_secret is None
        assert websub_podcast.websub_requested is None
        assert websub_podcast.num_websub_retries == 1
