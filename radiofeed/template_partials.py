import functools
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from radiofeed.types import HttpRequestResponse


def use_partial_for_target(*, target: str, partial: str) -> Callable:
    """Conditionally renders template partial if `target` matches HX-Target."""

    def _decorator(fn: HttpRequestResponse) -> HttpRequestResponse:
        @functools.wraps(fn)
        def _view(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            response = fn(request, *args, **kwargs)
            if hasattr(response, "render"):
                return render_partial_for_target(
                    request,
                    response,
                    target=target,
                    partial=partial,
                )
            return response

        return _view

    return _decorator


def render_partial_for_target(
    request: HttpRequest,
    response: TemplateResponse,
    *,
    target: str,
    partial: str,
) -> TemplateResponse:
    """Conditionally renders template partial if `target` matches HX-Target."""

    if request.htmx.target == target and not response.is_rendered:
        response.template_name += f"#{partial}"
    return response
