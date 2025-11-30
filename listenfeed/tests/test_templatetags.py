import pytest
from django.contrib.sites.models import Site
from django.template import RequestContext, TemplateSyntaxError

from listenfeed.templatetags import (
    cookie_banner,
    format_duration,
    fragment,
    render_attrs,
    websearch_clean,
)


@pytest.fixture
def req(rf, anonymous_user):
    req = rf.get("/")
    req.user = anonymous_user
    req.htmx = False
    req.site = Site.objects.get_current()
    return req


@pytest.fixture
def auth_req(req, user):
    req.user = user
    return req


class TestRenderAttrs:
    def test_empty(self):
        assert render_attrs({}) == ""

    def test_single(self):
        assert render_attrs({"class": "btn"}) == ' class="btn"'

    def test_default(self):
        assert render_attrs(None, **{"class": "btn"}) == ' class="btn"'

    def test_default_override(self):
        assert (
            render_attrs(
                {"class": "btn-primary"},
                **{"class": "btn"},
            )
            == ' class="btn-primary"'
        )

    def test_boolean(self):
        assert render_attrs({"required": True}) == " required"

    def test_multiple(self):
        attrs = {
            "class": "btn",
            "id": "submit-button",
            "data_toggle": "modal",  # underscore converted to hyphen
        }
        result = render_attrs(attrs)
        assert 'class="btn"' in result
        assert 'id="submit-button"' in result
        assert 'data-toggle="modal"' in result

    def test_false_value(self):
        assert render_attrs({"class": False}) == ""

    def test_none_value(self):
        assert render_attrs({"class": None}) == ""


class TestFragment:
    def test_render_no_template_obj(self, mocker):
        context = mocker.Mock()
        context.template = None
        with pytest.raises(TemplateSyntaxError):
            fragment(context, "header.html#title", "test")


class TestCookieBanner:
    def test_not_accepted(self, rf):
        req = rf.get("/")
        req.COOKIES = {}
        context = RequestContext(request=req)
        assert cookie_banner(context)["cookies_accepted"] is False

    def test_accepted(self, rf):
        req = rf.get("/")
        req.COOKIES = {"accept-cookies": True}
        context = RequestContext(request=req)
        assert cookie_banner(context)["cookies_accepted"] is True


class TestFormatDuration:
    @pytest.mark.parametrize(
        ("duration", "expected"),
        [
            pytest.param(0, "", id="zero"),
            pytest.param(30, "", id="30 seconds"),
            pytest.param(60, "1\xa0minute", id="1 minute"),
            pytest.param(61, "1\xa0minute", id="just over 1 minute"),
            pytest.param(90, "1\xa0minute", id="1 minute 30 seconds"),
            pytest.param(540, "9\xa0minutes", id="9 minutes"),
            pytest.param(2400, "40\xa0minutes", id="40 minutes"),
            pytest.param(3600, "1\xa0hour", id="1 hour"),
            pytest.param(9000, "2\xa0hours, 30\xa0minutes", id="2 hours 30 minutes"),
        ],
    )
    def test_format_duration(self, duration, expected):
        assert format_duration(duration) == expected


class TestWebsearchClean:
    @pytest.mark.parametrize(
        ("input_text", "expected"),
        [
            ("hello world", "hello world"),
            ("hello+world", "hello world"),
            ("hello-world", "hello world"),
            ("hello~world", "hello world"),
            ('"hello world"', "hello world"),
            ("'hello world'", "hello world"),
            ("(hello world)", "hello world"),
            ("<hello world>", "hello world"),
            ("hello AND world", "hello world"),
            ("hello OR world", "hello world"),
            ("hello NOT world", "hello world"),
            ("  hello   world  ", "hello world"),
            ("hello+world AND test-(example)", "hello world test example"),
        ],
    )
    def test_websearch_clean(self, input_text, expected):
        assert websearch_clean(input_text) == expected
