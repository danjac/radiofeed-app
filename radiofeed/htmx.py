from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from render_block import render_block_to_string


def render_blocks_to_response(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    use_blocks: list[str] | str,
    target: str | None = None,
    **response_kwargs,
) -> HttpResponse:
    """Renders template blocks instead of whole template for an HTMX request.

    If `use_blocks` is a `list`, will render each named template block in list.

    If `use_blocks` is a `str`, will render the specified template block.

    The list of blocks will be passed to the template context as `use_blocks`.

    If `target` is provided, will only render blocks if HX-Target HTTP header matches this target.

    If not an HTMX request or matching target will render the entire template.
    """
    if request.htmx and (target is None or target == request.htmx.target):
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
