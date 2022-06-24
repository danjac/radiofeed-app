from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts.parsers.models import (
    int_in_range,
    language_code,
    min_len,
    pub_date,
)


class TestLanguageCode:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("fr", "fr"),
            ("fr-CA", "fr"),
            ("", "en"),
        ],
    )
    def test_language_code(self, value, expected):
        assert language_code(value) == expected


class TestIntInRange:
    def test_too_low(self):
        with pytest.raises(ValueError):
            int_in_range(None, None, -2147483649)

    def test_too_high(self):
        with pytest.raises(ValueError):
            int_in_range(None, None, 2147483649)

    def test_ok(self):
        int_in_range(None, None, 1000)


class TestPubDate:
    def test_ok(self):
        pub_date(None, None, timezone.now() - timedelta(hours=1))

    def test_in_future(self):
        with pytest.raises(ValueError):
            pub_date(None, None, timezone.now() + timedelta(hours=1))


class TestMinLen:
    def test_ok(self):
        min_len(3)(None, None, [1, 2, 3])

    def test_too_small(self):
        with pytest.raises(ValueError):
            min_len(5)(None, None, [1, 2, 3])
