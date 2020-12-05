# Django
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.test import override_settings

# Third Party Libraries
import pytest

# Local
from ..ajax import AjaxRequestFragmentMiddleware
from ..http import HttpResponseNotAllowedMiddleware
from ..turbolinks import TurbolinksMiddleware

pytestmark = pytest.mark.django_db


@pytest.fixture
def get_response_not_allowed():
    def _get_response(req):
        return HttpResponseNotAllowed(permitted_methods=["POST"])

    return _get_response


class TestHttpResponseNotAllowedMiddleware:
    def test_405_debug_false(self, rf, get_response_not_allowed):
        req = rf.get("/")
        mw = HttpResponseNotAllowedMiddleware(get_response_not_allowed)
        with override_settings(DEBUG=True):
            resp = mw(req)
            assert b"Not Allowed" not in resp.content

    def test_405_debug_true(self, rf, get_response_not_allowed):
        req = rf.get("/")
        mw = HttpResponseNotAllowedMiddleware(get_response_not_allowed)
        with override_settings(DEBUG=False):
            resp = mw(req)
            assert b"Not Allowed" in resp.content

    def test_not_405(self, rf, get_response):
        req = rf.get("/")
        mw = HttpResponseNotAllowedMiddleware(get_response)
        with override_settings(DEBUG=False):
            resp = mw(req)
            assert b"Not Allowed" not in resp.content


class TestTurbolinksMiddleware:
    def test_location_header(self, rf, get_response):
        mw = TurbolinksMiddleware(get_response)
        req = rf.get("/")
        req.session = {"_turbolinks_redirect": "/"}
        resp = mw(req)
        assert resp["Turbolinks-Location"] == "/"

    def test_handle_redirect_if_turbolinks(self, rf):
        def get_response(req):
            return HttpResponseRedirect("/")

        mw = TurbolinksMiddleware(get_response)
        req = rf.get(
            "/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_TURBOLINKS_REFERRER="/",
        )
        resp = mw(req)
        assert resp["Content-Type"] == "text/javascript"

    def test_handle_redirect_if_not_turbolinks(self, rf):
        def get_response(req):
            return HttpResponseRedirect("/")

        mw = TurbolinksMiddleware(get_response)
        req = rf.get("/")
        req.session = {}
        resp = mw(req)
        assert resp["Location"] == "/"
        assert req.session["_turbolinks_redirect"] == "/"


class TestAjaxRequestFragmentMiddleware:
    def get_response(self):
        return lambda req: HttpResponseRedirect("/")

    def test_ajax_header_present(self, rf):
        mw = AjaxRequestFragmentMiddleware(self.get_response())
        req = rf.get(
            "/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_X_REQUEST_FRAGMENT="true",
        )
        mw(req)
        assert req.is_ajax_fragment

    def test_ajax_header_not_present(self, rf):
        mw = AjaxRequestFragmentMiddleware(self.get_response())
        req = rf.get(
            "/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        mw(req)
        assert not req.is_ajax_fragment

    def test_not_ajax_header_present(self, rf):
        mw = AjaxRequestFragmentMiddleware(self.get_response())
        req = rf.get(
            "/",
            HTTP_X_REQUEST_FRAGMENT="true",
        )
        mw(req)
        assert not req.is_ajax_fragment

    def test_not_ajax_header_not_present(self, rf):
        mw = AjaxRequestFragmentMiddleware(self.get_response())
        req = rf.get(
            "/",
        )
        mw(req)
        assert not req.is_ajax_fragment
