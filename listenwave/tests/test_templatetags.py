import pytest
from django.contrib.sites.models import Site
from django.template import TemplateSyntaxError

from listenwave.request import RequestContext
from listenwave.templatetags import cookie_banner, fragment


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
