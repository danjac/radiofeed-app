import pytest

from django.http import Http404
from django_htmx.middleware import HtmxDetails

from jcasts.common.asserts import assert_ok
from jcasts.common.paginate import paginate, render_paginated_list
from jcasts.podcasts.factories import PodcastFactory


@pytest.fixture
def podcasts(db):
    return PodcastFactory.create_batch(30)


class TestRenderPaginatedList:
    base_template = "podcasts/index.html"
    pagination_template = "podcasts/_podcasts.html"

    def test_render(self, rf, podcasts):
        req = rf.get("/")
        req.htmx = HtmxDetails(req)
        resp = render_paginated_list(
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
        resp = render_paginated_list(
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
        print(req.headers)
        resp = render_paginated_list(
            req,
            podcasts,
            self.base_template,
            self.pagination_template,
        )
        assert_ok(resp)
        assert resp.template_name == self.pagination_template


class TestPaginate:
    def test_paginate_first_page(self, rf, podcasts):
        page = paginate(rf.get("/"), podcasts, page_size=10)
        assert page.number == 1
        assert page.has_next()
        assert not page.has_previous()
        assert page.paginator.num_pages == 3

    def test_paginate_specified_page(self, rf, podcasts):
        page = paginate(rf.get("/", {"page": "2"}), podcasts, page_size=10)
        assert page.number == 2
        assert page.has_next()
        assert page.has_previous()
        assert page.paginator.num_pages == 3

    def test_paginate_invalid_page(self, rf, podcasts):
        with pytest.raises(Http404):
            paginate(
                rf.get("/", {"page": "fubar"}),
                podcasts,
                page_size=10,
            )
