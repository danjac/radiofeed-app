import http

from django.http import HttpResponse


class HttpResponseNoContent(HttpResponse):
    status_code: int = http.HTTPStatus.NO_CONTENT
