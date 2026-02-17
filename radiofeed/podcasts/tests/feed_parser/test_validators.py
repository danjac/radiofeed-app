from typing import Any

import pytest
from django.db.models import TextChoices

from radiofeed.parsers.feeds.validators import (
    default_if_none,
    is_one_of,
    normalize_url,
    one_of_choices,
    pg_integer,
)


class TestPgInteger:
    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [
            (123, 123),
            ("456", 456),
            (-2147483648, -2147483648),
            (2147483647, None),
            (2147483648, None),
            (-2147483649, None),
            ("not_an_integer", None),
            (None, None),
        ],
    )
    def test_pg_integer_valid(self, input_value: Any, expected: int | None) -> None:
        assert pg_integer(input_value) == expected


class TestIsOneOf:
    @pytest.mark.parametrize(
        ("input_value", "values", "expected"),
        [
            ("apple", ["apple", "banana", "cherry"], True),
            ("BANANA", ["apple", "banana", "cherry"], True),
            ("grape", ["apple", "banana", "cherry"], False),
            (None, ["apple", "banana", "cherry"], False),
            ("", ["apple", "banana", "cherry"], False),
        ],
    )
    def test_one_of_valid(
        self,
        input_value: str | None,
        values: list[str],
        *,
        expected: bool,
    ) -> None:
        assert is_one_of(input_value, values=values) == expected


class TestDefaultIfNone:
    @pytest.mark.parametrize(
        ("input_value", "default", "expected"),
        [
            (None, 10, 10),
            (5, 10, 5),
            ("test", "default", "test"),
            (None, "default", "default"),
        ],
    )
    def test_default_if_none_valid(
        self,
        input_value: Any,
        default: Any,
        *,
        expected: Any,
    ) -> None:
        assert default_if_none(input_value, default=default) == expected


class TestOneOfChoices:
    class SampleChoices(TextChoices):
        OPTION_A = "option_a"
        OPTION_B = "option_b"
        OPTION_C = "option_c"

    @pytest.mark.parametrize(
        ("input_value", "default", "expected"),
        [
            ("option_a", "option_b", "option_a"),
            ("OPTION_B", "option_a", "option_b"),
            ("invalid_option", "option_c", "option_c"),
            (None, "option_a", "option_a"),
            ("", "option_b", "option_b"),
        ],
    )
    def test_one_of_choices_valid(
        self,
        input_value: str | None,
        default: str,
        *,
        expected: str,
    ) -> None:
        assert (
            one_of_choices(
                input_value,
                choices=self.SampleChoices,
                default=default,
            )
            == expected
        )


class TestNormalizeUrl:
    @pytest.mark.parametrize(
        ("input_value", "expected"),
        [
            ("example.com", "http://example.com"),
            ("http://example.com", "http://example.com"),
            ("https://example.com", "https://example.com"),
            ("", ""),
            (None, ""),
            ("invalid-url", ""),
        ],
    )
    def test_url_valid(
        self,
        input_value: str | None,
        *,
        expected: str,
    ) -> None:
        assert normalize_url(input_value) == expected
