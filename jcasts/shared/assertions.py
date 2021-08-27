import functools
import http


def assert_status(response, status):
    assert response.status_code == status, response.content


assert_ok = functools.partial(assert_status, status=http.HTTPStatus.OK)

assert_not_found = functools.partial(assert_status, status=http.HTTPStatus.NOT_FOUND)

assert_gone = functools.partial(assert_status, status=http.HTTPStatus.GONE)

assert_conflict = functools.partial(assert_status, status=http.HTTPStatus.CONFLICT)

assert_bad_request = functools.partial(
    assert_status, status=http.HTTPStatus.BAD_REQUEST
)

assert_no_content = functools.partial(assert_status, status=http.HTTPStatus.NO_CONTENT)
