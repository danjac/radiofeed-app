from django.template.response import TemplateResponse
from django_htmx.middleware import HtmxDetails

from radiofeed.template_partials import render_partial_for_target


class TestRenderPartialForTarget:
    def test_render_full_template(self, rf):
        req = rf.get("/")
        req.htmx = HtmxDetails(req)
        response = render_partial_for_target(
            req,
            TemplateResponse(req, "index.html"),
            target="form",
            partial="form",
        )

        assert response.template_name == "index.html"

    def test_render_not_matching_target(self, rf):
        req = rf.get(
            "/",
            headers={"HX-Request": "true", "HX-Target": "my-form"},
        )
        req.htmx = HtmxDetails(req)
        response = render_partial_for_target(
            req,
            TemplateResponse(req, "index.html"),
            target="form",
            partial="form",
        )

        assert response.template_name == "index.html"

    def test_render_partial(self, rf):
        req = rf.get(
            "/",
            headers={"HX-Request": "true", "HX-Target": "form"},
        )
        req.htmx = HtmxDetails(req)
        response = render_partial_for_target(
            req,
            TemplateResponse(req, "index.html"),
            target="form",
            partial="form",
        )

        assert response.template_name == "index.html#form"
