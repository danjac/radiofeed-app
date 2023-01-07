from __future__ import annotations

import pytest

from radiofeed.common import encoder

_value = "https://example.com/cover/test.jpg"


class TestEncodeUrl:
    def test_encode(self):
        assert encoder.encode(_value)


class TestDecodeUrl:
    def test_ok(self):
        assert encoder.decode(encoder.encode(_value)) == _value

    def test_invalid(self):
        with pytest.raises(encoder.DecodeError):
            encoder.decode("bad key")
