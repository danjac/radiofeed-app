import http

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

require_form_methods = require_http_methods(["GET", "HEAD", "POST"])

require_DELETE = require_http_methods(["DELETE"])  # noqa: N816


class TextResponse(HttpResponse):
    """Plain text response."""

    def __init__(self, *args, **kwargs):
        """Initialize a plain text HTTP response."""
        kwargs.setdefault("content_type", "text/plain")
        super().__init__(*args, **kwargs)


class HttpResponseNoContent(HttpResponse):
    """204 No Content response."""

    status_code = http.HTTPStatus.NO_CONTENT


class HttpResponseUnauthorized(HttpResponse):
    """401 Unauthorized response."""

    status_code = http.HTTPStatus.UNAUTHORIZED


class HttpResponseConflict(HttpResponse):
    """409 Conflict response."""

    status_code = http.HTTPStatus.CONFLICT
