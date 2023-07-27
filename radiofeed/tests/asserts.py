import functools
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


def assert_status(response: HttpResponse, status: int) -> None:
    """Assert response status matches."""
    assert response.status_code == status, response.status_code


# Status assert shortcuts

assert_bad_request = functools.partial(assert_status, status=400)
assert_conflict = functools.partial(assert_status, status=409)
assert_not_found = functools.partial(assert_status, status=404)
assert_no_content = functools.partial(assert_status, status=204)
assert_ok = functools.partial(assert_status, status=200)
assert_unauthorized = functools.partial(assert_status, status=401)
assert_unprocessable_entity = functools.partial(assert_status, status=422)
