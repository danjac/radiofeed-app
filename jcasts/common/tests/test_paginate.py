import pytest

from django.http import Http404
from django_htmx.middleware import HtmxDetails

from jcasts.common.asserts import assert_ok
from jcasts.common.paginate import paginate
from jcasts.podcasts.factories import PodcastFactory


@pytest.fixture
def podcasts(db):
    return PodcastFactory.create_batch(30)


class TestPaginate:
    base_template = "podcasts/index.html"
    pagination_template = "podcasts/includes/podcasts.html"

    def test_render(self, rf, podcasts):
        req = rf.get("/")
        req.htmx = HtmxDetails(req)
        resp = paginate(
            req,
            podcasts,
            self.base_template,
            self.pagination_template,
        )
        assert_ok(resp)
        assert resp.template_name == self.base_template

    def test_render_htmx(self, rf, podcasts):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)
        resp = paginate(
            req,
            podcasts,
            self.base_template,
            self.pagination_template,
        )
        assert_ok(resp)
        assert resp.template_name == self.base_template

    def test_render_htmx_pagination_target(self, rf, podcasts):
        req = rf.get("/", HTTP_HX_REQUEST="true", HTTP_HX_TARGET="object-list")
        req.htmx = HtmxDetails(req)
        resp = paginate(
            req,
            podcasts,
            self.base_template,
            self.pagination_template,
        )
        assert_ok(resp)
        assert resp.template_name == self.pagination_template

    def test_paginate_invalid_page(self, rf, podcasts):
        with pytest.raises(Http404):
            paginate(
                rf.get("/", {"page": "fubar"}),
                podcasts,
                self.base_template,
                self.pagination_template,
                page_size=10,
            )
