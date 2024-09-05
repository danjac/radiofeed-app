import functools
import http

from django.http import HttpResponse


def assert_http_status(response: HttpResponse, status: http.HTTPStatus) -> None:
    assert status == response.status_code, f"{status} != {response.status_code}"


assert_200 = functools.partial(assert_http_status, status=http.HTTPStatus.OK)
assert_204 = functools.partial(assert_http_status, status=http.HTTPStatus.NO_CONTENT)
assert_400 = functools.partial(assert_http_status, status=http.HTTPStatus.BAD_REQUEST)
assert_401 = functools.partial(assert_http_status, status=http.HTTPStatus.UNAUTHORIZED)
assert_404 = functools.partial(assert_http_status, status=http.HTTPStatus.NOT_FOUND)
assert_409 = functools.partial(assert_http_status, status=http.HTTPStatus.CONFLICT)
