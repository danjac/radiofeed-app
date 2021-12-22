import pytest

from django.http import Http404

from jcasts.podcasts.factories import PodcastFactory
from jcasts.shared.assertions import assert_ok
from jcasts.shared.pagination import paginate, render_paginated_response


@pytest.fixture
def podcasts(db):
    return PodcastFactory.create_batch(30)


class TestRenderPaginationResponse:
    main_template = "podcasts/index.html"
    pagination_template = "podcasts/_podcasts.html"

    def test_render(self, rf, podcasts):
        req = rf.get("/", {"page": "2"})
        resp = render_paginated_response(
            req,
            podcasts,
            self.main_template,
            self.pagination_template,
            page_size=10,
        )
        assert_ok(resp)
        assert resp.template_name == self.main_template


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
