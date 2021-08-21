from __future__ import annotations

import http

from django.http import HttpResponse


class HttpResponseConflict(HttpResponse):
    status_code: int = http.HTTPStatus.CONFLICT


class HttpResponseNoContent(HttpResponse):
    status_code: int = http.HTTPStatus.NO_CONTENT
