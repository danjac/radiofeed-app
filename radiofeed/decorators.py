import functools
from collections.abc import Callable

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django_htmx.http import HttpResponseClientRedirect
from render_block import render_block_to_string

require_form_methods = require_http_methods(["GET", "HEAD", "POST"])

require_DELETE = require_http_methods(["DELETE"])  # noqa: N816


def render_htmx(*, use_blocks: list[str] | str, target: str | None = None) -> Callable:
    """Conditionally render blocks on HTMX request.

    If the response is a `TemplateResponse` instance will render the content using only the selected blocks.

    If `target` is provided, will also try to match the `HX-Target` header.
    """
    if isinstance(use_blocks, str):
        use_blocks = [use_blocks]

    def _decorator(view: Callable) -> Callable:
        @functools.wraps(view)
        def _wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            response = view(request, *args, **kwargs)
            if (
                hasattr(response, "render")
                and not response.is_rendered
                and request.htmx
                and (target is None or target == request.htmx.target)
            ):
                return HttpResponse(
                    [
                        render_block_to_string(
                            response.template_name,
                            block,
                            response.context_data,
                            request=request,
                        )
                        for block in use_blocks
                    ],
                    headers=response.headers,
                    status=response.status_code,
                )
            return response

        return _wrapper

    return _decorator


def require_auth(view: Callable) -> Callable:
    """Login required decorator also handling HTMX and AJAX views."""

    @functools.wraps(view)
    def _wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return view(request, *args, **kwargs)

        if request.htmx:
            return HttpResponseClientRedirect(
                redirect_to_login(settings.LOGIN_REDIRECT_URL).url
            )

        # plain non-HTMX AJAX: return a 401
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return HttpResponse(status=401)

        return redirect_to_login(request.get_full_path())

    return _wrapper
