from __future__ import annotations

import pytest

from radiofeed.utils.encoder import decode, encode


class TestEncode:
    def test_encode(self):
        assert encode("testing")


class TestDecode:
    def test_ok(self):
        assert decode(encode("testing")) == "testing"

    def test_bad_signing(self):
        with pytest.raises(ValueError):
            decode(
                "bHR0cHM6Ly9tZWdhcGhvbmUuaW1naXgubmV0L3BvZGNhc3RzL2IwOTEwZTMwLTMyNzgtMTFlYy05ZDUyLTViOGU5MzQ1MmFjYS9pbWFnZS9CVU5LRVJfVElMRVNfY29weV8yLnBuZz9peGxpYj1yYWlscy0yLjEuMiZtYXgtdz0zMDAwJm1heC1oPTMwMDAmZml0PWNyb3AmYXV0bz1mb3JtYXQsY29tcHJlc3M6TnNGdVZBTDFheTZ1OGs0VEpfV2ZsdXVZUEZ2T3Vockd2WnNuQVpZMk53SQ"
            )

    def test_bad_encoding(self):
        with pytest.raises(ValueError):
            decode("testing")
