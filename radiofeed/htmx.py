from django.http import HttpRequest
from django.template.response import TemplateResponse


def render_template_partial(
    request: HttpRequest,
    template_name: str,
    context: dict,
    *,
    partial: str = "",
    target: str = "",
    **response_kwargs,
) -> TemplateResponse:
    """Conditionally renders a named template partial instead of the
    full template, if the `target` matches the HX-Target header."""

    response = TemplateResponse(request, template_name, context, **response_kwargs)

    if partial and target and request.htmx.target == target:
        response.template_name += f"#{partial}"

    return response
