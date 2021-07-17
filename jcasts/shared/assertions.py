import functools
import http

from django.http import HttpResponse


def assert_status(response: HttpResponse, status: int) -> None:
    assert response.status_code == status, response.content


assert_ok = functools.partial(assert_status, status=http.HTTPStatus.OK)

assert_bad_request = functools.partial(
    assert_status, status=http.HTTPStatus.BAD_REQUEST
)

assert_no_content = functools.partial(assert_status, status=http.HTTPStatus.NO_CONTENT)
