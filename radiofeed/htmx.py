from typing import Any

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, resolve_url
from django_htmx.http import HttpResponseLocation
from render_block import render_block_to_string


def hx_redirect(
    request: HttpRequest, to: Any | None = None, *args, **kwargs
) -> HttpResponseLocation | HttpResponseRedirect:
    """Shortcut do resolve URL and return an HX-Location response.

    If not an HTMX request, returns a standard HttpResponseRedirect.

    If `to` is None, URL resolves to current path.
    """
    http_response_location_kwargs = {
        kw: kwargs.pop(kw, None)
        for kw in (
            "event",
            "headers",
            "source",
            "swap",
            "target",
            "values",
        )
    }

    url = resolve_url(to, *args, **kwargs) if to else request.path

    return (
        HttpResponseLocation(url, **http_response_location_kwargs)
        if request.htmx
        else HttpResponseRedirect(url)
    )


def hx_render(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    target: str | None = None,
    use_blocks: list[str] | None = None,
    status: int | None = None,
) -> HttpResponse:
    """Renders template blocks instead of whole template for an HTMX request.

    If not an HTMX request (HX-Request is not `true`) will render the entire template.

    If `target` is provided, will also try to match the HX-Target header.

    A list of the blocks rendered is added to template context as `use_blocks`.
    """

    matches_target = target is None or target == request.htmx.target
    use_blocks = use_blocks or []

    if use_blocks and request.htmx and matches_target:
        context = (context or {}) | {"use_blocks": use_blocks}
        return HttpResponse(
            [
                render_block_to_string(
                    template_name,
                    block,
                    context,
                    request=request,
                )
                for block in use_blocks
            ],
            status=status,
        )

    return render(request, template_name, context, status=status)
