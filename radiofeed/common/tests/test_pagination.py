from __future__ import annotations

import pytest

from django.http import Http404
from django_htmx.middleware import HtmxDetails
from pytest_django.asserts import assertTemplateUsed

from radiofeed.common.asserts import assert_ok
from radiofeed.common.pagination import pagination_url, render_pagination_response
from radiofeed.podcasts.factories import PodcastFactory


@pytest.fixture
def podcasts(db):
    return PodcastFactory.create_batch(30)


class TestPaginationUrl:
    def test_append_page_number_to_querystring(self, rf):

        req = rf.get("/search/", {"q": "test"})
        url = pagination_url(req, 5)
        assert url.startswith("/search/?")
        assert "q=test" in url
        assert "p=5" in url


class TestRenderPaginationResponse:
    base_template = "podcasts/index.html"
    pagination_template = "podcasts/pagination/podcasts.html"

    def test_render(self, rf, podcasts):
        req = rf.get("/")
        req.htmx = HtmxDetails(req)
        with assertTemplateUsed(self.base_template):
            resp = render_pagination_response(
                req,
                podcasts,
                self.base_template,
                self.pagination_template,
            )

        assert_ok(resp)

    def test_render_htmx(self, rf, podcasts):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)
        with assertTemplateUsed(self.base_template):
            resp = render_pagination_response(
                req,
                podcasts,
                self.base_template,
                self.pagination_template,
            )

        assert_ok(resp)

    def test_render_htmx_pagination_target(self, rf, podcasts):
        req = rf.get("/", HTTP_HX_REQUEST="true", HTTP_HX_TARGET="object-list")
        req.htmx = HtmxDetails(req)
        with assertTemplateUsed(self.pagination_template):
            resp = render_pagination_response(
                req,
                podcasts,
                self.base_template,
                self.pagination_template,
            )
        assert_ok(resp)

    def test_invalid_page(self, rf, podcasts):
        req = rf.get("/", {"p": "fubar"})
        req.htmx = HtmxDetails(req)
        with pytest.raises(Http404):
            render_pagination_response(
                req,
                podcasts,
                self.base_template,
                self.pagination_template,
                page_size=10,
            )
