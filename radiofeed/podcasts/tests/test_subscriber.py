from __future__ import annotations

import dataclasses
import hmac
import http
import uuid

import pytest
import requests

from radiofeed.podcasts import subscriber
from radiofeed.podcasts.factories import create_podcast


@dataclasses.dataclass
class MockResponse:
    status_code: int

    def raise_for_status(self):
        if self.status_code not in range(200, 400):
            raise requests.HTTPError("oops")


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
            "requests.get",
            return_value=MockResponse(status_code=http.HTTPStatus.ACCEPTED),
        )

        subscriber.subscribe(podcast)

        podcast.refresh_from_db()

        assert podcast.websub_requested
        assert podcast.websub_secret

    def test_error(self, mocker, podcast):
        mocker.patch(
            "requests.get",
            return_value=MockResponse(status_code=http.HTTPStatus.NOT_FOUND),
        )

        with pytest.raises(requests.HTTPError):
            subscriber.subscribe(podcast)

        podcast.refresh_from_db()

        assert podcast.websub_requested is None
        assert podcast.websub_secret is None
