from django_htmx.middleware import HtmxDetails

from listenwave.partials import render_partial_response


class TestRenderPartialResponse:
    def test_target_matches(self, rf):
        request = rf.get("/", HTTP_HX_TARGET="target", HTTP_HX_REQUEST="true")
        request.htmx = HtmxDetails(request)

        response = render_partial_response(
            request,
            "template.html",
            target="target",
            partial="partial",
        )
        assert response.template_name == "template.html#partial"

    def test_target_not_matches(self, rf):
        request = rf.get("/", HTTP_HX_TARGET="other", HTTP_HX_REQUEST="true")
        request.htmx = HtmxDetails(request)

        response = render_partial_response(
            request,
            "template.html",
            target="target",
            partial="partial",
        )
        assert response.template_name == "template.html"

    def test_target_not_htmx(self, rf):
        request = rf.get("/")
        request.htmx = HtmxDetails(request)

        response = render_partial_response(
            request,
            "template.html",
            target="target",
            partial="partial",
        )
        assert response.template_name == "template.html"
