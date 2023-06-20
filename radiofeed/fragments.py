from django.http import HttpRequest, HttpResponse
from render_block import render_block_to_string


def render_template_fragments(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    use_blocks: list[str] | None = None,
    status: int | None = None,
) -> HttpResponse:
    """Renders HTMX fragments.

    Individual template blocks in the template are rendered instead of the whole template.

    A list of the blocks rendered is passed into the template context as `rendered_template_blocks`.
    """

    use_blocks = use_blocks or []

    context = {
        **(context or {}),
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
        status=status,
    )
