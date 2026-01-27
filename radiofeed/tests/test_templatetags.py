import pytest
from django.contrib.sites.models import Site
from django.template import TemplateSyntaxError

from radiofeed.request import RequestContext
from radiofeed.templatetags import cookie_banner, format_duration, fragment


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
