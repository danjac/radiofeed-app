import pytest
from django_htmx.middleware import HtmxDetails

from radiofeed.middleware import PaginationDetails
from radiofeed.pagination import render_pagination_response
from radiofeed.podcasts.tests.factories import create_podcast
from radiofeed.tests.factories import create_batch


class TestRenderPaginationResponse:
    @pytest.fixture()
    def podcasts(self):
        return create_batch(create_podcast, 12)

    @pytest.mark.django_db()
    def test_not_htmx(self, rf, podcasts):
        req = rf.get("/")
        req.htmx = False

        req.pagination = PaginationDetails(req)

        response = render_pagination_response(req, podcasts, "index.html")
        assert response.template_name == "index.html"
        assert response.context_data["page_obj"].object_list == podcasts
        assert response.context_data["pagination_target"] == "pagination"

    @pytest.mark.django_db()
    def test_htmx_matches_pagination_target(self, rf, podcasts):
        req = rf.get("/", HTTP_HX_REQUEST="true", HTTP_HX_TARGET="pagination")

        req.htmx = HtmxDetails(req)
        req.pagination = PaginationDetails(req)

        response = render_pagination_response(req, podcasts, "index.html")
        assert response.template_name == "index.html#pagination"
        assert response.context_data["page_obj"].object_list == podcasts
        assert response.context_data["pagination_target"] == "pagination"
