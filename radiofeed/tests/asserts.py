import http
import json

from django.http import HttpResponse


def assert_hx_redirect(response: HttpResponse, url: str) -> None:
    """Asserts HX-Redirect header matches url."""
    assert "HX-Redirect" in response, response.headers
    assert response["HX-Redirect"] == url, response.headers


def assert_hx_location(response: HttpResponse, data: dict) -> None:
    """Asserts values in HX-Location"""
    assert "HX-Location" in response, response.headers
    location = json.loads(response.headers["HX-Location"])
    assert data == location, location


def assert_ok(response: HttpResponse) -> None:
    assert http.HTTPStatus(response.status_code).is_success


def assert_client_error(response: HttpResponse) -> None:
    assert http.HTTPStatus(response.status_code).is_client_error
