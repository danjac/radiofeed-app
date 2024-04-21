import http

import pytest
from django.http import HttpResponse
from django.urls import reverse

from radiofeed.decorators import require_auth


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
        req.htmx = True

        response = view(req)
        assert response["HX-Redirect"] == reverse("account_login")

    def test_anonymous_plain_ajax(self, rf, anonymous_user, view):
        req = rf.get("/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        req.user = anonymous_user
        req.htmx = False
        response = view(req)
        assert response.status_code == http.HTTPStatus.UNAUTHORIZED

    @pytest.mark.django_db()
    def test_authenticated(self, rf, user, view):
        req = rf.get("/")
        req.user = user
        response = view(req)
        assert response.status_code == http.HTTPStatus.OK
