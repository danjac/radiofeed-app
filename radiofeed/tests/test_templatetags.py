import json

import pytest
from django.contrib.sites.models import Site
from django.template.context import Context, RequestContext
from django.utils.html import format_html

from radiofeed.middleware import DeferredHTMLMiddleware
from radiofeed.templatetags import (
    absolute_uri,
    csrf_header,
    deferred,
    format_duration,
    render_deferred,
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


class TestCsrfHeader:
    def test_header(self, rf, mocker, settings):
        settings.CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"
        mocker.patch("radiofeed.templatetags.get_token", return_value="abc123")
        req = rf.get("/")
        value = csrf_header(RequestContext(req), value=1)
        assert json.loads(value) == {"X-CSRFTOKEN": "abc123", "value": 1}


class TestFormatDuration:
    @pytest.mark.parametrize(
        ("duration", "expected"),
        [
            pytest.param(0, "", id="zero"),
            pytest.param(30, "", id="30 seconds"),
            pytest.param(60, "1 minute", id="1 minute"),
            pytest.param(61, "1 minute", id="just over 1 minute"),
            pytest.param(90, "1 minute", id="1 minute 30 seconds"),
            pytest.param(540, "9 minutes", id="9 minutes"),
            pytest.param(2400, "40 minutes", id="40 minutes"),
            pytest.param(3600, "1 hour", id="1 hour"),
            pytest.param(
                9000,
                "2 hours 30 minutes",
                id="2 hours 30 minutes",
            ),
        ],
    )
    def test_format_duration(self, duration, expected):
        assert format_duration(duration) == expected


class TestAbsoluteUri:
    @pytest.mark.django_db
    def test_plain_url_from_request(self, rf):
        req = rf.get("/")
        assert (
            absolute_uri(RequestContext(req), "/podcasts/")
            == "http://example.com/podcasts/"
        )

    @pytest.mark.django_db
    def test_object_from_request(self, rf):
        req = rf.get("/")
        assert (
            absolute_uri(RequestContext(req), "/podcasts/")
            == "http://example.com/podcasts/"
        )

    @pytest.mark.django_db
    def test_plain_url_from_site(self, settings):
        settings.USE_HTTPS = False
        assert absolute_uri(Context(), "/podcasts/") == "http://example.com/podcasts/"

    @pytest.mark.django_db
    def test_https_from_site(self, settings):
        settings.USE_HTTPS = True
        assert absolute_uri(Context(), "/podcasts/") == "https://example.com/podcasts/"

    @pytest.mark.django_db
    def test_object_from_site(self, podcast, settings):
        settings.USE_HTTPS = False
        assert (
            absolute_uri(Context(), podcast)
            == f"http://example.com{podcast.get_absolute_url()}"
        )


class TestRenderDeferred:
    def test_render_deferred_no_content(self, rf, get_response):
        req = rf.get("/")
        context = RequestContext(req)
        DeferredHTMLMiddleware(get_response)(req)

        assert render_deferred(context, "js") == ""

    def test_render_deferred_with_content(self, rf, get_response):
        req = rf.get("/")
        context = RequestContext(req)
        DeferredHTMLMiddleware(get_response)(req)
        content = format_html("<script>console.log('Hello')</script>")

        deferred(context, content, "js")

        assert render_deferred(context, "js") == content
        assert render_deferred(context, "js") == "", "deferred content not cleared"
