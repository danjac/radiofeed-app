from datetime import timedelta

import pytest

from django.utils import timezone

from radiofeed.podcasts.parsers import converters


class TestText:
    def test_ok(self):
        assert converters.text(["", "ok"]) == "ok"

    def test_default(self):
        assert converters.text(["", ""], default="full") == "full"

    def test_required(self):
        with pytest.raises(ValueError):
            converters.text([""], required=True)


class TestPubDate:
    def test_not_date(self):
        with pytest.raises(ValueError):
            converters.pub_date(["invalid"])

    def test_invalid_date(self):
        with pytest.raises(ValueError):
            converters.pub_date(["Sun, 28 Apr 2013 15:12:352 CST"])

    def test_in_future(self):
        with pytest.raises(ValueError):
            converters.pub_date([(timezone.now() + timedelta(days=3)).strftime("%c")])

    def test_ok(self):
        assert converters.pub_date(["Fri, 19 Jun 2020 16:58:03 +0000"])


class TestAudio:
    @pytest.mark.parametrize(
        "value,raises",
        [
            ("", True),
            ("video/mp4", True),
            ("audio/mp3", False),
        ],
    )
    def test_parse_audio(self, value, raises):
        if raises:
            with pytest.raises(ValueError):
                converters.audio(value)
        else:
            assert converters.audio([value]) == value

    def test_take_first_correct(self):
        assert converters.audio(["video/mpeg", "audio/mp3"]) == "audio/mp3"


class TestDuration:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("", ""),
            ("invalid", ""),
            ("300", "300"),
            ("10:30", "10:30"),
            ("10:30:59", "10:30:59"),
            ("10:30:99", "10:30"),
        ],
    )
    def test_parse_duration(self, value, expected):
        assert converters.duration([value]) == expected


class TestInteger:
    @pytest.mark.parametrize(
        "value,expected,required",
        [
            ("1234", 1234, False),
            ("0", 0, False),
            ("-111111111111111", None, False),
            ("111111111111111", None, False),
            ("", None, False),
            ("a string", None, False),
            ("-111111111111111", None, True),
            ("111111111111111", None, True),
            ("", None, True),
            ("a string", None, True),
        ],
    )
    def test_integer(self, value, expected, required):
        if required:
            with pytest.raises(ValueError):
                converters.integer([value], required=True)
        else:

            assert converters.integer([value]) == expected

    def test_take_first_correct(self):
        assert converters.integer(["invalid", "", "1234"]) == 1234


class TestUrl:
    @pytest.mark.parametrize(
        "value,expected,required,raises",
        [
            ("http://example.com", "http://example.com", False, False),
            ("http://example.com", "http://example.com", True, False),
            ("example", None, True, True),
            ("example", None, False, False),
        ],
    )
    def test_parse_url(self, value, expected, required, raises):
        if required:
            if raises:
                with pytest.raises(ValueError):
                    converters.url(value, required=True)
            else:
                converters.url([value], required=True)

        else:
            assert converters.url([value]) == expected

    def test_take_first_correct(self):
        assert (
            converters.url(["invalid", "https://example.com"]) == "https://example.com"
        )


class TestLanguage:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("en-GB", "en"),
            ("FI-FI", "fi"),
            ("fr", "fr"),
            ("fr-CA", "fr"),
            ("xx", "en"),
            ("", "en"),
            ("#", "en"),
        ],
    )
    def test_language(self, value, expected):
        assert converters.language([value]) == expected

    def test_take_first_correct(self):
        assert converters.language("x", "ro") == "ro"


class TestBoolean:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("yes", True),
            ("no", False),
            ("", False),
        ],
    )
    def test_boolean(self, value, expected):
        assert converters.boolean([value]) is expected


class TestExplicit:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("clean", True),
            ("yes", True),
            ("no", False),
            ("", False),
        ],
    )
    def test_explicit(self, value, expected):
        assert converters.explicit([value]) is expected
