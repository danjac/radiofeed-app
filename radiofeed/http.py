from django.http import HttpResponse


class HttpResponseNoContent(HttpResponse):
    """304 No Content response."""

    status_code = 204


class HttpResponseConflict(HttpResponse):
    """409 Conflict response."""

    status_code = 409
