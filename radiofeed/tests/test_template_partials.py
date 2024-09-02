from django_htmx.middleware import HtmxDetails

from radiofeed.template_partials import render_template_partial


def add_htmx_details(req):
    req.htmx = HtmxDetails(req)
    return req


class TestRenderTemplatePartial:
    def test_render_not_htmx(self, rf):
        response = render_template_partial(
            add_htmx_details(rf.get("/")),
            "index.html",
            partial="form",
            target="my-form",
        )

        assert response.template_name == "index.html"

    def test_render_target__matching(self, rf):
        response = render_template_partial(
            add_htmx_details(
                rf.get(
                    "/",
                    HTTP_HX_REQUEST="true",
                    HTTP_HX_TARGET="my-form",
                )
            ),
            "index.html",
            partial="form",
            target="my-form",
        )

        assert response.template_name == "index.html#form"

    def test_render_target_not_matching(self, rf):
        response = render_template_partial(
            add_htmx_details(
                rf.get(
                    "/",
                    HTTP_HX_REQUEST="true",
                    HTTP_HX_TARGET="other-form",
                )
            ),
            "index.html",
            partial="form",
            target="my-form",
        )

        assert response.template_name == "index.html"
