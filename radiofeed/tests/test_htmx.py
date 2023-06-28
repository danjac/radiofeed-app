from django_htmx.middleware import HtmxDetails

from radiofeed.asserts import assert_hx_location
from radiofeed.htmx import hx_redirect


class TestHxRedirect:
    def test_htmx(self, rf):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.htmx = HtmxDetails(req)

        assert_hx_location(
            hx_redirect(req, "/", swap="outerHTML"),
            {
                "path": "/",
                "swap": "outerHTML",
            },
        )

    def test_not_htmx(self, rf):
        req = rf.get("/")
        req.htmx = HtmxDetails(req)
        resp = hx_redirect(req, "/", swap="outerHTML")
        assert resp["Location"] == "/"
