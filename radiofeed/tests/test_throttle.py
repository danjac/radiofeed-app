import http

import pytest
from django.http import HttpResponse

from radiofeed.throttle import get_ident, throttle
from radiofeed.users.models import User


class TestThrottle:
    @pytest.fixture
    def view(self):
        @throttle(limit=10, duration=60)
        def _view(_):
            return HttpResponse("OK")

        return _view

    def test_ok_no_count(self, rf, anonymous_user, view):
        req = rf.get("/")
        req.user = anonymous_user
        response = view(req)
        assert response.status_code == http.HTTPStatus.OK

    def test_throttled_under_count(self, rf, anonymous_user, view, mocker):
        mocker.patch("django.core.cache.cache.get", return_value=5)
        req = rf.get("/")
        req.user = anonymous_user

        view(req)
        response = view(req)
        assert response.status_code == http.HTTPStatus.OK

    def test_throttled_ip_addr_over_count(self, rf, anonymous_user, view, mocker):
        mocker.patch("django.core.cache.cache.get", return_value=12)
        req = rf.get("/")
        req.user = anonymous_user

        view(req)
        response = view(req)
        assert response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS


class TestGetIdent:
    def test_authenticated(self, rf):
        req = rf.get("/")
        req.user = User(id=1)
        assert get_ident(req) == f"user:{req.user.pk}"

    def test_x_forwarded(self, rf, anonymous_user):
        req = rf.get("/", HTTP_X_FORWARDED_FOR="8.8.8.8")
        req.user = anonymous_user
        assert get_ident(req) == "ip:8.8.8.8"

    def test_remote_addr(self, rf, anonymous_user):
        req = rf.get("/")
        req.user = anonymous_user
        assert get_ident(req) == "ip:127.0.0.1"
