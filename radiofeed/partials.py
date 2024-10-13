from django.http import HttpRequest
from django.template.response import TemplateResponse


def render_partial_for_target(
    request: HttpRequest, response: TemplateResponse, *, target: str, partial: str
) -> TemplateResponse:
    """Conditionally renders a template partial if `target` matches the HX-Target header.

    Otherwise renders the full template.
    """

    if request.htmx.target == target and isinstance(response.template_name, str):
        response.template_name += f"#{partial}"

    return response
