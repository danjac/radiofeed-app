from __future__ import annotations

import datetime

import box

from jcasts.podcasts.coerce import (
    coerce_bool,
    coerce_date,
    coerce_int,
    coerce_list,
    coerce_str,
    coerce_url,
)


class TestCoerce:
    def test_coerce_str(self):
        assert coerce_str("testing") == "testing"

    def test_coerce_str_limit(self):
        assert coerce_str("testing", limit=4) == "test"

    def test_coerce_str_multiple(self):
        assert coerce_str("", None, "testing", "another") == "testing"

    def test_coerce_str_none(self):
        assert coerce_str(None) == ""

    def test_coerce_str_box(self):
        assert coerce_str(box.Box({})) == ""

    def test_coerce_bool_is_none(self):
        assert coerce_bool(None) is False

    def test_coerce_bool_is_empty(self):
        assert coerce_bool("") is False

    def test_coerce_bool_is_false(self):
        assert coerce_bool(False) is False

    def test_coerce_bool_is_true(self):
        assert coerce_bool(True) is True

    def test_coerce_bool_is_not_empty(self):
        assert coerce_bool("yes") is True

    def test_coerce_str_is_none(self):
        assert coerce_str(None) == ""

    def test_coerce_int(self):
        assert coerce_int("123") == 123

    def test_coerce_int_multiple(self):
        assert coerce_int("foo", None, "123", "456", 989) == 123

    def test_coerce_int_is_none(self):
        assert coerce_int(None) is None

    def test_coerce_int_invalid(self):
        assert coerce_int("fubar") is None

    def test_coerce_url(self):
        assert coerce_url("http://example.com") == "http://example.com"

    def test_coerce_url_invalid(self):
        assert coerce_url("ftp://example.com") == ""

    def test_coerce_url_none(self):
        assert coerce_url(None) == ""

    def test_coerce_date(self):
        assert isinstance(coerce_date("Fri, 19 Jun 2020 16:58:03"), datetime.datetime)

    def test_coerce_date_invalid(self):
        assert coerce_date("fubar") is None

    def test_coerce_date_none(self):
        assert coerce_date(None) is None

    def test_coerce_list(self):
        assert coerce_list(["test"]) == ["test"]

    def test_coerce_list_none(self):
        assert coerce_list(None) == []
