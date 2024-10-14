import functools
import http

from django.http import HttpResponse


def assert_status(response: HttpResponse, status: http.HTTPStatus) -> None:
    """Assert that the response has the expected status code."""
    assert (
        response.status_code == status
    ), f"Expected status {status}, but got {response.status_code}"


assert200 = functools.partial(assert_status, status=http.HTTPStatus.OK)
assert401 = functools.partial(assert_status, status=http.HTTPStatus.UNAUTHORIZED)
assert404 = functools.partial(assert_status, status=http.HTTPStatus.NOT_FOUND)
assert409 = functools.partial(assert_status, status=http.HTTPStatus.CONFLICT)
