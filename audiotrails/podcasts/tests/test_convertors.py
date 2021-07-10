from __future__ import annotations

import datetime

from audiotrails.podcasts.convertors import (
    conv_bool,
    conv_date,
    conv_int,
    conv_list,
    conv_str,
    conv_url,
)


class TestConvertors:
    def test_conv_str(self):
        assert conv_str("testing") == "testing"

    def test_conv_bool_is_none(self):
        assert conv_bool(None) is False

    def test_conv_bool_is_empty(self):
        assert conv_bool("") is False

    def test_conv_bool_is_false(self):
        assert conv_bool(False) is False

    def test_conv_bool_is_true(self):
        assert conv_bool(True) is True

    def test_conv_bool_is_not_empty(self):
        assert conv_bool("yes") is True

    def test_conv_str_is_none(self):
        assert conv_str(None) == ""

    def test_conv_int(self):
        assert conv_int("123") == 123

    def test_conv_int_is_none(self):
        assert conv_int(None) is None

    def test_conv_int_invalid(self):
        assert conv_int("fubar") is None

    def test_conv_url(self):
        assert conv_url("http://example.com") == "http://example.com"

    def test_conv_url_invalid(self):
        assert conv_url("ftp://example.com") == ""

    def test_conv_url_none(self):
        assert conv_url(None) == ""

    def test_conv_date(self):
        assert isinstance(conv_date("Fri, 19 Jun 2020 16:58:03"), datetime.datetime)

    def test_conv_date_invalid(self):
        assert conv_date("fubar") is None

    def test_conv_date_none(self):
        assert conv_date(None) is None

    def test_conv_list(self):
        assert conv_list(["test"]) == ["test"]

    def test_conv_list_none(self):
        assert conv_list(None) == []
