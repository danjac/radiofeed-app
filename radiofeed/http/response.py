import http
from typing import TypeAlias

from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse

RenderOrRedirectResponse: TypeAlias = TemplateResponse | HttpResponseRedirect


class TextResponse(HttpResponse):
    """Plain text response."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize a plain text HTTP response."""
        kwargs.setdefault("content_type", "text/plain")
        super().__init__(*args, **kwargs)


class HttpResponseNoContent(HttpResponse):
    """204 No Content response."""

    status_code = http.HTTPStatus.NO_CONTENT


class HttpResponseConflict(HttpResponse):
    """409 Conflict response."""

    status_code = http.HTTPStatus.CONFLICT
