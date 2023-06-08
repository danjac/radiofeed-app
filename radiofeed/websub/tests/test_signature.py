import hmac
import uuid

import pytest

from radiofeed.websub.signature import InvalidSignature, check_signature


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

        check_signature(req, secret)

    def test_secret_is_none(self, rf, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        with pytest.raises(InvalidSignature):
            check_signature(req, secret=None)

    def test_signature_mismatch(self, rf, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        with pytest.raises(InvalidSignature):
            check_signature(req, secret=uuid.uuid4())

    def test_content_length_too_large(self, rf, secret, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            CONTENT_LENGTH=2000000000,
            HTTP_X_HUB_SIGNATURE=f"sha1={signature}",
        )

        with pytest.raises(InvalidSignature):
            check_signature(req, secret)

    def test_hub_signature_header_missing(self, rf, secret):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
        )

        with pytest.raises(InvalidSignature):
            check_signature(req, secret)

    def test_invalid_algo(self, rf, secret, signature):
        req = rf.post(
            "/",
            self.body,
            content_type=self.content_type,
            HTTP_X_HUB_SIGNATURE=f"sha1111={signature}",
        )

        with pytest.raises(InvalidSignature):
            check_signature(req, secret)
