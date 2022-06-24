from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts.parsers import validators


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
                validators.not_empty(None, None, value)
        else:
            validators.not_empty(None, None, value)


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
                validators.url(None, None, value)
        else:
            validators.url(None, None, value)


class TestPubDate:
    def test_ok(self):
        validators.pub_date(None, None, timezone.now() - timedelta(hours=1))

    def test_in_future(self):
        with pytest.raises(ValueError):
            validators.pub_date(None, None, timezone.now() + timedelta(hours=1))
