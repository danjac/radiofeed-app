import pytest

from django.http import Http404
from django_htmx.middleware import HtmxDetails

from jcasts.podcasts.factories import PodcastFactory
from jcasts.shared.assertions import assert_ok
from jcasts.shared.pagination import paginate, render_paginated_response


@pytest.fixture
def podcasts(db):
    return PodcastFactory.create_batch(30)


class TestRenderPaginationResponse:
    main_template = "podcasts/index.html"
    pagination_template = "podcasts/_podcasts.html"

    def test_is_not_htmx(self, rf, podcasts):
        req = rf.get("/", {"page": "2"})
        req.htmx = HtmxDetails(req)
        resp = render_paginated_response(
            req,
            podcasts,
            self.main_template,
            self.pagination_template,
            page_size=10,
        )
        assert_ok(resp)
        assert resp.template_name == self.main_template
        assert "is_paginated" not in resp.context_data

    def test_is_htmx(self, rf, podcasts):
        req = rf.get(
            "/",
            {"page": "2"},
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="page-2",
        )
        req.htmx = HtmxDetails(req)
        resp = render_paginated_response(
            req,
            podcasts,
            self.main_template,
            self.pagination_template,
            page_size=10,
        )
        assert_ok(resp)
        assert resp.template_name == self.pagination_template
        assert "is_paginated" in resp.context_data


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
