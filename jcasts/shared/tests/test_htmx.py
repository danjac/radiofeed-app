import json

import pytest

from django.http import HttpResponse

from jcasts.shared.htmx import with_hx_trigger


class TestWithHxTrigger:
    @pytest.fixture
    def response(self):
        return HttpResponse()

    def test_no_data(self, response):
        response = with_hx_trigger(response, "")
        assert "HX-Trigger" not in response

    def test_string(self, response):
        response = with_hx_trigger(response, "reload-queue")
        assert json.loads(response["HX-Trigger"]) == {"reload-queue": ""}

    def test_dict(self, response):
        response = with_hx_trigger(response, {"remove-queue-item": 1})
        assert json.loads(response["HX-Trigger"]) == {"remove-queue-item": 1}

    def test_append_to_string(self, response):
        response["HX-Trigger"] = "testme"
        response = with_hx_trigger(response, {"remove-queue-item": 1})
        assert json.loads(response["HX-Trigger"]) == {
            "remove-queue-item": 1,
            "testme": "",
        }

    def test_append_to_dict(self, response):
        response["HX-Trigger"] = json.dumps({"testme": "test"})
        response = with_hx_trigger(response, {"remove-queue-item": 1})
        assert json.loads(response["HX-Trigger"]) == {
            "remove-queue-item": 1,
            "testme": "test",
        }
