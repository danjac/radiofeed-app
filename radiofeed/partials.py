from django.template.response import TemplateResponse

from radiofeed.http.request import HttpRequest


def render_partial_response(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    target: str,
    partial: str,
    **response_kwargs,
) -> TemplateResponse:
    """Conditionally renders a template partial if `target` matches the HX-Target header.

    Otherwise renders the full template.
    """
    if target and request.htmx.target == target:
        template_name += f"#{partial}"

    return TemplateResponse(
        request,
        template_name,
        context or {},
        **response_kwargs,
    )
