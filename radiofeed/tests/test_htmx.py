import json

from radiofeed.htmx import HttpResponseLocationRedirect


class TestHttpResponseLocationRedirect:
    def test_htmx(self, rf):
        req = rf.get("/")
        req.htmx = True
        resp = HttpResponseLocationRedirect(req, "/")
        assert resp.status_code == 200
        assert json.loads(resp["HX-Location"]) == {"path": "/"}
        assert "Location" not in resp

    def test_not_htmx(self, rf):
        req = rf.get("/")
        req.htmx = False
        resp = HttpResponseLocationRedirect(req, "/")
        assert resp.status_code == 302
        assert resp["Location"] == "/"
        assert "HX-Location" not in resp
