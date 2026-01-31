import functools
import http
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpResponse


def assert_status(response: HttpResponse, status: http.HTTPStatus) -> None:
    """Assert that the response has the expected status code."""
    assert response.status_code == status, (
        f"Expected status {status}, but got {response.status_code}"
    )


assert200 = functools.partial(assert_status, status=http.HTTPStatus.OK)
assert204 = functools.partial(assert_status, status=http.HTTPStatus.NO_CONTENT)
assert400 = functools.partial(assert_status, status=http.HTTPStatus.BAD_REQUEST)
assert401 = functools.partial(assert_status, status=http.HTTPStatus.UNAUTHORIZED)
assert404 = functools.partial(assert_status, status=http.HTTPStatus.NOT_FOUND)
assert409 = functools.partial(assert_status, status=http.HTTPStatus.CONFLICT)
