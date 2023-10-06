from django.http import HttpRequest
from django.template.response import TemplateResponse


def render_htmx(
    request: HttpRequest,
    template_name: str,
    context: dict | None,
    *,
    partial: str,
    target: str | None = None,
    **kwargs,
) -> TemplateResponse:
    """Conditionally render a template partial on HTMX request.

    If the response is a `TemplateResponse` instance will render the content using only the selected partial.

    If `target` is provided, will also try to match the `HX-Target` header.
    """

    if request.htmx and (target is None or target == request.htmx.target):
        template_name = f"{template_name}#{partial}"

    return TemplateResponse(request, template_name, context, **kwargs)
