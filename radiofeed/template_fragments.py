from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from render_block import render_block_to_string


def render_template_fragments(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    use_blocks: list[str] | None = None,
    use_templates: list[str] | None = None,
) -> HttpResponse:
    """Renders HTMX fragments."""

    use_blocks = use_blocks or []
    use_templates = use_templates or []

    context = context or {}

    return HttpResponse(
        [
            render_block_to_string(
                template_name,
                block,
                context,
                request=request,
            )
            for block in use_blocks
        ]
        + [
            render_to_string(template_name, context, request=request)
            for template_name in use_templates
        ]
    )
