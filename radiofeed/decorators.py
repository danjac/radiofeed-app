import functools
import http
from collections.abc import Callable

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django_htmx.http import HttpResponseClientRedirect
from render_block import render_block_to_string

require_form_methods = require_http_methods(["GET", "HEAD", "POST"])

require_DELETE = require_http_methods(["DELETE"])  # noqa


def for_htmx(*, target: str | None = None, use_blocks: str | list[str]) -> Callable:
    """
    If response is a `TemplateResponse`, will return specified template blocks instead of the whole template for an HTMX request.

    If `target` is specified, then will also try to match the target against the `HX-Target`.

    If not an HTMX request or the target does not match, will just return the entire content of the response.

    A list of all rendered blocks are added to the template context as `use_blocks`.
    """
    if isinstance(use_blocks, str):
        use_blocks = [use_blocks]

    use_blocks = use_blocks or []

    def _decorator(view: Callable) -> Callable:
        def _wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            response = view(request, *args, **kwargs)

            if not hasattr(response, "render"):
                # not SimpleTemplateResponse subclass
                return response

            matches_target = target is None or target == request.htmx.target

            if not request.htmx or not matches_target:
                return response

            context = response.context_data | {"use_blocks": use_blocks}

            return HttpResponse(
                [
                    render_block_to_string(
                        response.template_name,
                        block,
                        context,
                        request=request,
                    )
                    for block in use_blocks
                ],
                status=response.status_code,
                headers=response.headers,
            )

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
            return HttpResponse(status=http.HTTPStatus.UNAUTHORIZED)

        return redirect_to_login(request.get_full_path())

    return _wrapper
