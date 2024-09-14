from django.http import HttpRequest
from django.template.response import TemplateResponse


def render_partial_for_target(
    request: HttpRequest, response: TemplateResponse, *, target: str, partial: str
):
    """Conditionally renders a template partial if `target` matches the HX-Target header.

    Otherwise renders the full template.
    """

    if request.htmx.target == target:
        if isinstance(response.template_name, (list, tuple)):
            response.template_name = [
                f"{template_name}#{partial}" for template_name in response.template_name
            ]
        elif isinstance(response.template_name, str):
            response.template_name += f"#{partial}"

    return response
