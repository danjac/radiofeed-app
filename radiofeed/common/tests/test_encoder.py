from __future__ import annotations

import pytest

from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from radiofeed.common import encoder

_value = "https://example.com/cover/test.jpg"


class TestEncodeUrl:
    def test_encode(self):
        assert encoder.encode(_value)


class TestDecodeUrl:
    def test_ok(self):
        assert encoder.decode(encoder.encode(_value)) == _value

    def test_invalid(self):
        with pytest.raises(ValueError):
            encoder.decode("bad key")

    def test_bad_signature(self):

        encoded = urlsafe_base64_encode(force_bytes(_value))

        with pytest.raises(ValueError):
            encoder.decode(encoded)
