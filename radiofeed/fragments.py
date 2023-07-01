from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from render_block import render_block_to_string


def render_template_fragments(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    target: str | None = None,
    use_blocks: list[str] | None = None,
    use_templates: list[str] | None = None,
    **response_kwargs,
) -> HttpResponse:
    """Renders template blocks or individual templates instead of whole template for an HTMX request.

    If not an HTMX request (HX-Request is not `true`) will render the entire template in a `TemplateResponse`.

    If `target` is provided, will also try to match the HX-Target header.

    A list of blocks or templates rendered are added to template context as `use_blocks` and `use_templates`.
    """

    if (
        request.htmx
        and (use_blocks or use_templates)
        and (target is None or target == request.htmx.target)
    ):
        context = (context or {}) | {
            "use_blocks": use_blocks,
            "use_templates": use_templates,
        }
        return HttpResponse(
            [
                render_block_to_string(
                    template_name,
                    block,
                    context,
                    request=request,
                )
                for block in use_blocks or []
            ]
            + [
                render_to_string(template_name, context, request=request)
                for template_name in use_templates or []
            ],
            **response_kwargs,
        )
    return TemplateResponse(request, template_name, context, **response_kwargs)
