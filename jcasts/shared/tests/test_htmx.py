import http
import json

import pytest

from django.http import HttpResponse

from jcasts.shared.htmx import hx_redirect_to_login, with_hx_trigger


class TestHxRedirectToLogin:
    def test_with_default(self):
        resp = hx_redirect_to_login()
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        assert resp["HX-Refresh"] == "true"
        assert resp["HX-Redirect"] == "/account/login/?next=/"

    def test_with_url(self):
        url = "/final/"
        resp = hx_redirect_to_login(url)
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        assert resp["HX-Refresh"] == "true"
        assert resp["HX-Redirect"] == "/account/login/?next=/final/"


class TestWithHxTrigger:
    @pytest.fixture
    def response(self):
        return HttpResponse()

    def test_no_data(self, response):
        response = with_hx_trigger(response, "")
        assert "HX-Trigger" not in response

    def test_string(self, response):
        response = with_hx_trigger(response, "reload")
        assert json.loads(response["HX-Trigger"]) == {"reload": ""}

    def test_dict(self, response):
        response = with_hx_trigger(response, {"remove-item": 1})
        assert json.loads(response["HX-Trigger"]) == {"remove-item": 1}

    def test_append_to_string(self, response):
        response["HX-Trigger"] = "testme"
        response = with_hx_trigger(response, {"remove-item": 1})
        assert json.loads(response["HX-Trigger"]) == {
            "remove-item": 1,
            "testme": "",
        }

    def test_append_to_dict(self, response):
        response["HX-Trigger"] = json.dumps({"testme": "test"})
        response = with_hx_trigger(response, {"remove-item": 1})
        assert json.loads(response["HX-Trigger"]) == {
            "remove-item": 1,
            "testme": "test",
        }
