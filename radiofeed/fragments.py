from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from render_block import render_block_to_string


def render_template_fragments(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    target: str | None = None,
    use_blocks: list | str | None = None,
    **response_kwargs,
) -> HttpResponse:
    """Renders template blocks instead of whole template for an HTMX request.

    If `use_blocks` is a `list`, will render each named template block in list.

    If `use_blocks` is a `str`,  will render the specified template block.

    If `target` is provided, will render template blocks if HX-Target matches `target`.

    If not an HTMX request or no matching blocks found will render the entire template.
    """

    if (
        request.htmx
        and use_blocks
        and (target is None or target == request.htmx.target)
    ):
        if isinstance(use_blocks, str):
            use_blocks = [use_blocks]

        context = (context or {}) | {
            "use_blocks": use_blocks,
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
    return TemplateResponse(request, template_name, context, **response_kwargs)
