from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from render_block import render_block_to_string


def render_template_fragments(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    use_blocks: list[str] | None = None,
    **response_kwargs,
) -> HttpResponse:
    """Renders HTMX fragments.

    Individual template blocks in the template are rendered instead of the whole template.

    A list of the blocks rendered is passed into the template context as `rendered_template_blocks`.
    """

    use_blocks = use_blocks or []

    context = (context or {}) | {
        "rendered_template_blocks": use_blocks,
    }

    return HttpResponse(
        [
            render_block_to_string(
                template_name,
                block,
                context,
                request=request,
            )
            for block in use_blocks
        ],
        **response_kwargs,
    )


def render_fragments_if_target(
    request: HttpRequest,
    template_name: str,
    target: str,
    context: dict | None = None,
    *,
    use_blocks: list[str] | None = None,
    **response_kwargs,
) -> HttpResponse:
    """Conditionally renders fragment blocks if HX-Target matches `target`, otherwise returns full HTML response."""

    return (
        render_template_fragments(
            request,
            template_name,
            context,
            use_blocks=use_blocks,
            **response_kwargs,
        )
        if request.htmx.target == target
        else TemplateResponse(request, template_name, context, **response_kwargs)
    )
