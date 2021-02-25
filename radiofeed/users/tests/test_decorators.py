import http

import pytest
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from ..decorators import ajax_login_required


@ajax_login_required
def ajax_view(request):
    return HttpResponse("OK")


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
