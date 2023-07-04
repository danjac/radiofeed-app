import pytest
from django.http import HttpResponse
from django.urls import reverse
from django_htmx.middleware import HtmxDetails

from radiofeed.decorators import require_auth
from radiofeed.tests.asserts import assert_hx_redirect, assert_ok, assert_unauthorized


class TestRequireAuth:
    @pytest.fixture()
    def view(self):
        return require_auth(lambda req: HttpResponse())

    def test_anonymous_default(self, rf, anonymous_user, view):
        req = rf.get("/new/")
        req.user = anonymous_user
        req.htmx = False
        assert view(req).url == f"{reverse('account_login')}?next=/new/"

    def test_anonymous_htmx(self, rf, anonymous_user, view):
        req = rf.post("/new/", HTTP_HX_REQUEST="true")
        req.user = anonymous_user
        req.htmx = HtmxDetails(req)
        assert_hx_redirect(view(req), f"{reverse('account_login')}?next=/podcasts/")

    def test_anonymous_plain_ajax(self, rf, anonymous_user, view):
        req = rf.get("/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        req.user = anonymous_user
        req.htmx = False
        resp = view(req)
        assert_unauthorized(resp)

    @pytest.mark.django_db()
    def test_authenticated(self, rf, user, view):
        req = rf.get("/")
        req.user = user
        assert_ok(view(req))
