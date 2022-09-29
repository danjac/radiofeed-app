from __future__ import annotations

import pytest

from django.http import HttpResponse
from django.urls import reverse

from radiofeed.common.asserts import assert_hx_redirect, assert_ok, assert_unauthorized
from radiofeed.common.decorators import ajax_login_required


class TestAjaxLoginRequired:
    @pytest.fixture
    def ajax_view(self):
        return ajax_login_required(lambda req: HttpResponse())

    def test_anonymous_htmx(self, rf, anonymous_user, ajax_view):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.user = anonymous_user
        req.htmx = True
        assert_hx_redirect(ajax_view(req), f"{reverse('account_login')}?next=/")

    def test_anonymous_plain_ajax(self, rf, anonymous_user, ajax_view):
        req = rf.get("/")
        req.user = anonymous_user
        req.htmx = False
        resp = ajax_view(req)
        assert_unauthorized(resp)

    def test_authenticated(self, rf, user, ajax_view):
        req = rf.get("/")
        req.user = user
        assert_ok(ajax_view(req))
