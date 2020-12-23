# Django
from django.http import HttpResponseNotAllowed
from django.test import override_settings

# Third Party Libraries
import pytest

# Local
from ..http import HttpResponseNotAllowedMiddleware

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
