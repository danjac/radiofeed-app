import http

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

require_form_methods = require_http_methods(["GET", "HEAD", "POST"])

require_DELETE = require_http_methods(["DELETE"])  # noqa: N816


class HttpResponseTooManyRequests(HttpResponse):
    """429 Too Many Requests response."""

    status_code = http.HTTPStatus.TOO_MANY_REQUESTS


class HttpResponseNoContent(HttpResponse):
    """204 No Content response."""

    status_code = http.HTTPStatus.NO_CONTENT


class HttpResponseUnauthorized(HttpResponse):
    """401 Unauthorized response."""

    status_code = http.HTTPStatus.UNAUTHORIZED


class HttpResponseConflict(HttpResponse):
    """409 Conflict response."""

    status_code = http.HTTPStatus.CONFLICT
