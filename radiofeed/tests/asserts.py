import functools
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


def assert_response_status(response: HttpResponse, status: http.HTTPStatus) -> None:
    """Checks expected HTTP response status."""
    assert response.status_code == status


assert_response_bad_request = functools.partial(
    assert_response_status,
    status=http.HTTPStatus.BAD_REQUEST,
)


assert_response_conflict = functools.partial(
    assert_response_status,
    status=http.HTTPStatus.CONFLICT,
)

assert_response_no_content = functools.partial(
    assert_response_status,
    status=http.HTTPStatus.NO_CONTENT,
)


assert_response_not_found = functools.partial(
    assert_response_status,
    status=http.HTTPStatus.NOT_FOUND,
)

assert_response_ok = functools.partial(
    assert_response_status,
    status=http.HTTPStatus.OK,
)


assert_response_unauthorized = functools.partial(
    assert_response_status,
    status=http.HTTPStatus.UNAUTHORIZED,
)
