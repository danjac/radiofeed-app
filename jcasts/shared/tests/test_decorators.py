import http

import pytest

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import reverse

from jcasts.shared.decorators import ajax_login_required


@ajax_login_required
def my_ajax_view(request):
    return HttpResponse()


class TestAjaxLoginRequired:
    def test_anonymous_htmx(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        req.htmx = True
        resp = my_ajax_view(req)
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        assert (
            resp.headers["HX-Redirect"] == f"{reverse('account_login')}?next=/podcasts/"
        )
        assert resp.headers["HX-Refresh"] == "true"

    def test_anonymous_plain_ajax(self, rf, anonymous_user):
        req = rf.get("/", HTTP_HX_REQUEST="true")
        req.user = anonymous_user
        req.htmx = False
        with pytest.raises(PermissionDenied):
            my_ajax_view(req)

    def test_authenticated(self, rf, user):
        req = rf.get("/")
        req.user = user
        assert my_ajax_view(req).status_code == http.HTTPStatus.OK
