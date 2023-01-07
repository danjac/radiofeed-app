from __future__ import annotations

import pytest

from radiofeed.common import url_encoder

_url = "https://example.com/cover/test.jpg"


class TestEncodeUrl:
    def test_encode(self):
        assert url_encoder.encode_url(_url)


class TestDecodeUrl:
    def test_ok(self):
        assert url_encoder.decode_url(url_encoder.encode_url(_url)) == _url

    def test_error(self):
        with pytest.raises(url_encoder.DecodeError):
            url_encoder.decode_url("bad string")
