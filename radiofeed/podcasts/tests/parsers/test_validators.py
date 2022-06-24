from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts.parsers.validators import int_in_range, not_empty, pub_date, url


class TestNotEmpty:
    @pytest.mark.parametrize(
        "value,raises",
        [
            ("ok", False),
            ("", True),
            (None, True),
        ],
    )
    def test_not_empty(self, value, raises):

        if raises:
            with pytest.raises(ValueError):
                not_empty(None, None, value)
        else:
            not_empty(None, None, value)


class TestUrl:
    @pytest.mark.parametrize(
        "value,raises",
        [
            ("http://example.com", False),
            ("https://example.com", False),
            (None, False),
            ("example", True),
        ],
    )
    def test_url(self, value, raises):
        if raises:
            with pytest.raises(ValueError):
                url(None, None, value)
        else:
            url(None, None, value)


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
