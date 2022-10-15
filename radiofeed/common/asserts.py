from __future__ import annotations

import functools
import http

from django.http import HttpResponse


def assert_hx_redirect(response: HttpResponse, url: str) -> None:
    """Asserts HX-Redirect header matches url."""
    assert "HX-Redirect" in response and response["HX-Redirect"] == url  # nosec


def assert_status(response: HttpResponse, status: http.HTTPStatus) -> None:
    """Assert response status matches."""
    assert response.status_code == status, response.content  # nosec


(
    assert_bad_request,
    assert_conflict,
    assert_not_found,
    assert_no_content,
    assert_ok,
    assert_unauthorized,
) = (
    functools.partial(assert_status, status=status)
    for status in (
        http.HTTPStatus.BAD_REQUEST,
        http.HTTPStatus.CONFLICT,
        http.HTTPStatus.NOT_FOUND,
        http.HTTPStatus.NO_CONTENT,
        http.HTTPStatus.OK,
        http.HTTPStatus.UNAUTHORIZED,
    )
)
