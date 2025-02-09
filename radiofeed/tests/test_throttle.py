import http

import pytest
from django.http import HttpResponse

from radiofeed.throttle import throttle


class TestThrottle:
    @pytest.fixture
    def view(self):
        @throttle(1)
        def _view(_):
            return HttpResponse("OK")

        return _view

    def test_ok_anon(self, rf, anonymous_user, view):
        req = rf.get("/")
        req.user = anonymous_user
        response = view(req)
        assert response.status_code == http.HTTPStatus.OK

    def test_throttled_anon(self, rf, anonymous_user, view, mocker):
        mocker.patch("django.core.cache.cache.get", return_value=True)
        req = rf.get("/")
        req.user = anonymous_user

        view(req)
        response = view(req)
        assert response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS

    @pytest.mark.django_db
    def test_ok_user(self, rf, user, view):
        req = rf.get("/")
        req.user = user
        response = view(req)
        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.django_db
    def test_throttled_user(self, rf, user, view, mocker):
        mocker.patch("django.core.cache.cache.get", return_value=True)
        req = rf.get("/")
        req.user = user

        view(req)
        response = view(req)
        assert response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS
