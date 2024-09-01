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
    """Conditionally renders template partial if HX-Target header matches `target`.

    Otherwise renders entire template.
    """

    response = TemplateResponse(request, template_name, context, **response_kwargs)

    if request.htmx.target == target:
        response.template_name += f"#{partial}"

    return response
