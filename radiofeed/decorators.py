import functools

from django.http import HttpRequest, HttpResponse

from radiofeed.types import HttpRequestResponse


def use_template_partial(*, partial: str, target: str):
    """Conditionally returns template partial, if `target` matches HX-Target.

    This will only work if the response is a `SimpleTemplateResponse` subclass - other HttpResponse types will be ignored.
    """

    def _decorator(fn: HttpRequestResponse) -> HttpRequestResponse:
        @functools.wraps(fn)
        def _wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            response = fn(request, *args, **kwargs)
            if hasattr(response, "template_name") and request.htmx.target == target:
                response.template_name += f"#{partial}"
            return response

        return _wrapper

    return _decorator
