import http

import pytest

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from ..decorators import ajax_login_required, with_new_user_cta


@ajax_login_required
def ajax_view(request):
    return HttpResponse("OK")


@with_new_user_cta
def cta_view(request):
    return HttpResponse("OK")


class TestWithNewUserCTA:
    def test_is_authenticated(self, rf, user_model):
        req = rf.get("/")
        req.user = user_model()
        resp = cta_view(req)
        assert not req.show_new_user_cta
        assert resp.status_code == http.HTTPStatus.OK

    def test_is_anonymous(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        resp = cta_view(req)
        assert req.show_new_user_cta
        assert resp.status_code == http.HTTPStatus.OK

    def test_is_anonymous_has_cookie(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        req.COOKIES["new-user-cta"] = "true"
        resp = cta_view(req)
        assert not req.show_new_user_cta
        assert resp.status_code == http.HTTPStatus.OK


class TestAjaxLoginRequired:
    def test_is_authenticated(self, rf, user_model):
        req = rf.get("/")
        req.user = user_model()
        resp = ajax_view(req)
        assert resp.status_code == http.HTTPStatus.OK

    def test_is_anonymous(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        with pytest.raises(PermissionDenied):
            ajax_view(req)
