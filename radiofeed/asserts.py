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


def assert_status(response: HttpResponse, status: http.HTTPStatus) -> None:
    """Assert response status matches."""
    assert response.status_code == status, response.status_code


(
    assert_bad_request,
    assert_conflict,
    assert_not_found,
    assert_no_content,
    assert_ok,
    assert_unauthorized,
    assert_unprocessable_entity,
) = (
    functools.partial(assert_status, status=status)
    for status in (
        http.HTTPStatus.BAD_REQUEST,
        http.HTTPStatus.CONFLICT,
        http.HTTPStatus.NOT_FOUND,
        http.HTTPStatus.NO_CONTENT,
        http.HTTPStatus.OK,
        http.HTTPStatus.UNAUTHORIZED,
        http.HTTPStatus.UNPROCESSABLE_ENTITY,
    )
)
