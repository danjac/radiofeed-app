from __future__ import annotations

import dataclasses
import hmac
import http
import uuid
from datetime import timedelta

import pytest
import requests
from django.utils import timezone
from faker import Faker

from radiofeed.podcasts import websub
from radiofeed.podcasts.factories import create_podcast

_faker = Faker()


@dataclasses.dataclass
class MockResponse:
    status_code: int

    def raise_for_status(self):
        if self.status_code not in range(200, 400):
            raise requests.HTTPError("oops")


class TestGetPodcastsForSubscribe:
    hub = "https://example.com/"

    @pytest.mark.django_db
    def test_not_websub(self, db, podcast):
        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_expired_none(self, db):
        create_podcast(
            websub_hub=self.hub, websub_expires=None, websub_mode="subscribe"
        )
        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_expired(self, db):
        create_podcast(
            websub_hub=self.hub,
            websub_expires=timezone.now() - timedelta(days=1),
            websub_mode="subscribe",
        )

        assert websub.get_podcasts_for_subscribe().count() == 1

    @pytest.mark.django_db
    def test_too_many_errors(self, db):
        create_podcast(
            websub_hub=self.hub,
            websub_expires=timezone.now() - timedelta(days=1),
            websub_mode="subscribe",
            num_websub_retries=3,
        )

        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_expired_not_subscribed(self, db):
        create_podcast(
            websub_hub=self.hub,
            websub_expires=timezone.now() - timedelta(days=1),
            websub_mode="unsubscribe",
        )

        assert websub.get_podcasts_for_subscribe().count() == 0

    @pytest.mark.django_db
    def test_not_expired(self, db):
        create_podcast(
            websub_hub=self.hub,
            websub_expires=timezone.now() + timedelta(days=1),
            websub_mode="subscribe",
        )

        assert websub.get_podcasts_for_subscribe().count() == 0


class TestCheckSignature:
    body = b"testme"
    content_type = "application/xml"

    @pytest.fixture
    def podcast(self, db):
        return create_podcast(websub_secret=uuid.uuid4())

    @pytest.mark.django_db
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

        assert websub.check_signature(req, podcast)

    @pytest.mark.django_db
    def test_signature_mismatch(self, rf, podcast):
        sig = hmac.new(uuid.uuid4().hex.encode("utf-8"), self.body, "sha1").hexdigest()

        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={sig}",
        )

        assert not websub.check_signature(req, podcast)

    @pytest.mark.django_db
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

        assert not websub.check_signature(req, podcast)

    @pytest.mark.django_db
    def test_hub_signature_header_missing(self, rf, podcast):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
        )

        assert not websub.check_signature(req, podcast)

    @pytest.mark.django_db
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

        assert not websub.check_signature(req, podcast)


class TestSubscribe:
    hub = "https://example.com/hub/"

    @pytest.fixture
    def websub_podcast(self):
        return create_podcast(websub_hub=self.hub)

    @pytest.mark.django_db
    def test_accepted(self, mocker, websub_podcast):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        websub.subscribe(websub_podcast)

        websub_podcast.refresh_from_db()

        assert websub_podcast.websub_mode == "subscribe"
        assert websub_podcast.websub_expires
        assert websub_podcast.websub_secret

    @pytest.mark.django_db
    def test_websub_hub_none(self, mocker):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        podcast = create_podcast()

        websub.subscribe(podcast)

        podcast.refresh_from_db()

        assert podcast.websub_mode == ""
        assert podcast.websub_expires is None
        assert podcast.websub_secret is None

    @pytest.mark.django_db
    def test_unsubscribe(self, mocker, websub_podcast):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        websub.subscribe(websub_podcast, mode="unsubscribe")

        websub_podcast.refresh_from_db()

        assert websub_podcast.websub_mode == "unsubscribe"
        assert websub_podcast.websub_expires is None
        assert websub_podcast.websub_secret

    @pytest.mark.django_db
    def test_error(self, mocker, websub_podcast):
        mocker.patch(
            "requests.post",
            return_value=MockResponse(status_code=http.HTTPStatus.NOT_FOUND),
        )

        with pytest.raises(requests.HTTPError):
            websub.subscribe(websub_podcast)

        websub_podcast.refresh_from_db()

        assert websub_podcast.websub_mode == ""
        assert websub_podcast.websub_expires is None
        assert websub_podcast.websub_secret is None

        assert websub_podcast.num_websub_retries == 1
