from __future__ import annotations

import http

from django.http import HttpResponse


class HttpResponseConflict(HttpResponse):
    """HTTP CONFLICT response."""

    status_code: int = http.HTTPStatus.CONFLICT


class HttpResponseNoContent(HttpResponse):
    """HTTP NO CONTENT response."""

    status_code: int = http.HTTPStatus.NO_CONTENT


class HttpResponseUnauthorized(HttpResponse):
    """HTTP UNAUTHORIZED response."""

    status_code: int = http.HTTPStatus.UNAUTHORIZED
