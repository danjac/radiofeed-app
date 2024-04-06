from django_htmx.middleware import HtmxDetails

from radiofeed.htmx import HtmxTemplateResponse


class TestHtmxTemplateResponse:
    def test_not_htmx(self, rf):
        req = rf.get("/")
        req.htmx = False

        response = HtmxTemplateResponse(req, "index.html")
        assert response.template_name == "index.html"

    def test_htmx(self, rf):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)
        response = HtmxTemplateResponse(req, "index.html", partial="form")
        assert response.template_name == "index.html#form"

    def test_htmx_partial_none(self, rf):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)
        response = HtmxTemplateResponse(req, "index.html")
        assert response.template_name == "index.html"

    def test_htmx_matches_target(self, rf):
        req = rf.get("/", HTTP_HX_REQUEST="true", HTTP_HX_TARGET="form")
        req.htmx = HtmxDetails(req)
        response = HtmxTemplateResponse(
            req, "index.html", partial="form", target="form"
        )
        assert response.template_name == "index.html#form"

    def test_htmx_not_matching_target(self, rf):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)
        response = HtmxTemplateResponse(
            req, "index.html", partial="form", target="form"
        )
        assert response.template_name == "index.html"
