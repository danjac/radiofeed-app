import pytest
from django_htmx.middleware import HtmxDetails

from radiofeed.htmx import render_template_partial


class TestRenderTemplatePartial:
    @pytest.fixture
    def view(self):
        return lambda request: render_template_partial(
            request, "index.html", partial="form", target="form"
        )

    def test_full_template_rendered(self, rf, view):
        req = rf.get("/")
        req.htmx = HtmxDetails(req)
        response = view(req)
        assert response.template_name == "index.html"

    def test_target_match(self, rf, view):
        req = rf.get("/", HTTP_HX_REQUEST="true", HTTP_HX_TARGET="form")
        req.htmx = HtmxDetails(req)
        response = view(req)
        assert response.template_name == "index.html#form"

    def test_no_target_match(self, rf, view):
        req = rf.get("/", HTTP_HX_REQUEST="true", HTTP_HX_TARGET="div")
        req.htmx = HtmxDetails(req)
        response = view(req)
        assert response.template_name == "index.html"
