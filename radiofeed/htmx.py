from django.http import HttpRequest
from django.template.response import TemplateResponse


def render_htmx(
    request: HttpRequest,
    template_name: str,
    context: dict | None,
    *,
    partial: str | None = None,
    target: str | None = None,
    **kwargs,
) -> TemplateResponse:
    """Conditionally render a template partial on HTMX request.

    If `partial` is provided, and HX-Request in header, will render the template partial, otherwise will render the entire template.

    If `target` is provided, will also try to match the `HX-Target` header.
    """

    if partial and request.htmx and (target is None or target == request.htmx.target):
        template_name = f"{template_name}#{partial}"

    return TemplateResponse(request, template_name, context, **kwargs)
