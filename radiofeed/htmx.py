from django.http import HttpRequest
from django.template.response import TemplateResponse


def render_template_partial(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    partial: str,
    target: str,
    **response_kwargs,
) -> TemplateResponse:
    """Conditionally renders a template partial rather than the entire template,
    if `target` matches HX-Target header."""
    response = TemplateResponse(request, template_name, context, **response_kwargs)
    if target == request.htmx.target:
        response.template_name += f"#{partial}"
    return response
