import http

from django.http import HttpResponse


class HttpResponseConflict(HttpResponse):
    status_code: int = http.HTTPStatus.CONFLICT


class HttpResponseNoContent(HttpResponse):
    status_code: int = http.HTTPStatus.NO_CONTENT


class HttpResponseUnauthorized(HttpResponse):
    status_code: int = http.HTTPStatus.UNAUTHORIZED
