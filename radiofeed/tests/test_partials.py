from django.template.response import TemplateResponse
from django_htmx.middleware import HtmxDetails

from radiofeed.partials import render_partial_for_target


class TestRenderPartialForTarget:
    def test_not_htmx(self, rf):
        req = rf.get("/")
        req.htmx = HtmxDetails(req)
        response = render_partial_for_target(
            req,
            TemplateResponse(req, "index.html"),
            target="form",
            partial="form",
        )
        assert response.template_name == "index.html"

    def test_htmx_target_match(self, rf):
        req = rf.get("/", headers={"HX-Request": "true", "HX-Target": "form"})
        req.htmx = HtmxDetails(req)
        response = render_partial_for_target(
            req,
            TemplateResponse(req, "index.html"),
            target="form",
            partial="form",
        )
        assert response.template_name == "index.html#form"

    def test_htmx_target_match_is_list(self, rf):
        req = rf.get("/", headers={"HX-Request": "true", "HX-Target": "form"})
        req.htmx = HtmxDetails(req)
        response = render_partial_for_target(
            req,
            TemplateResponse(req, ["index.html", "other/index.html"]),
            target="form",
            partial="form",
        )
        assert response.template_name == ["index.html#form", "other/index.html#form"]

    def test_htmx_target_not_match(self, rf):
        req = rf.get("/", headers={"HX-Request": "true", "HX-Target": "my-form"})
        req.htmx = HtmxDetails(req)
        response = render_partial_for_target(
            req,
            TemplateResponse(req, "index.html"),
            target="form",
            partial="form",
        )
        assert response.template_name == "index.html"
