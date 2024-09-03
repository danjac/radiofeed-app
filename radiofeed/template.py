import functools

from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from radiofeed.typing import HttpRequestResponse


def use_partial_for_target(*, target: str, partial: str) -> HttpRequestResponse:
    """Conditionally renders template partial if `target` matches HX-Target."""

    def _decorator(fn: HttpRequestResponse) -> HttpRequestResponse:
        @functools.wraps(fn)
        def _wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            response = fn(request, *args, **kwargs)
            if hasattr(response, "render"):
                return render_partial_for_target(
                    request,
                    response,
                    target=target,
                    partial=partial,
                )
            return response

        return _wrapper

    return _decorator


def render_partial_for_target(
    request: HttpRequest,
    response: TemplateResponse,
    *,
    target: str,
    partial: str,
) -> TemplateResponse:
    """Conditionally renders template partial if `target` matches HX-Target."""

    if request.htmx.target == target:
        response.template_name += f"#{partial}"
    return response
