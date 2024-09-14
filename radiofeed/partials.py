from django.http import HttpRequest
from django.template.response import TemplateResponse


def render_partial_for_target(
    request: HttpRequest, response: TemplateResponse, *, target: str, partial: str
):
    """Conditionally renders a template partial if `target` matches the HX-Target header.

    Otherwise renders the full template.
    """

    if request.htmx.target == target:
        template_name = (
            response.template_name[0]
            if isinstance(response.template_name, (list, tuple))
            else response.template_name
        )
        response.template_name = f"{template_name}#{partial}"
    return response
