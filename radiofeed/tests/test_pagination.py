from __future__ import annotations

import pytest

from django.http import Http404
from django_htmx.middleware import HtmxDetails
from pytest_django.asserts import assertTemplateUsed

from radiofeed.asserts import assert_ok
from radiofeed.pagination import FastCountPaginator, render_pagination_response
from radiofeed.podcasts.factories import PodcastFactory
from radiofeed.podcasts.models import Podcast


@pytest.fixture
def podcasts(db):
    return PodcastFactory.create_batch(30)


class TestFastCountPaginator:
    def test_with_fast_count(self, podcasts):
        paginator = FastCountPaginator(Podcast.objects.all(), 10)
        assert paginator.count == 30


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
        with pytest.raises(Http404):
            render_pagination_response(
                rf.get("/", {"page": "fubar"}),
                podcasts,
                self.base_template,
                self.pagination_template,
                page_size=10,
            )
