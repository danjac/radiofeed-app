import http

import pytest

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from audiotrails.common.decorators import ajax_login_required


@ajax_login_required
def my_ajax_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse()


class TestAjaxLoginRequired:
    def test_anonymous(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        with pytest.raises(PermissionDenied):
            my_ajax_view(req)

    def test_authenticated(self, rf, user):
        req = rf.get("/")
        req.user = user
        assert my_ajax_view(req).status_code == http.HTTPStatus.OK
