import http

from django.http import HttpResponse


class HttpResponseNoContent(HttpResponse):
    """304 No Content response."""

    status_code = http.HTTPStatus.NO_CONTENT


class HttpResponseConflict(HttpResponse):
    """409 Conflict response."""

    status_code = http.HTTPStatus.CONFLICT
