import http

from django.http import HttpResponse


class HttpResponseNoContent(HttpResponse):
    """204 No Content response."""

    status_code = http.HTTPStatus.NO_CONTENT


class HttpResponseUnauthorized(HttpResponse):
    """401 Unauthorized response."""

    status_code = http.HTTPStatus.UNAUTHORIZED


class HttpResponseConflict(HttpResponse):
    """409 Conflict response."""

    status_code = http.HTTPStatus.CONFLICT
