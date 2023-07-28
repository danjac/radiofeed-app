from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from render_block import render_block_to_string


def render_template_blocks(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    use_blocks: list[str] | str,
    target: str | None = None,
    **response_kwargs,
) -> HttpResponse:
    """Returns HTMX blocks instead of full template if request has HX-Request header.

    If `target` is provided will return blocks only if HX-Target header matches this value.

    Adds `use_blocks` to template context if any.
    """

    # if matching target/blocks, render template blocks
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
