from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from render_block import render_block_to_string


def render_template_fragments(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    target: str | None = None,
    use_blocks: list[str] | None = None,
    **response_kwargs,
) -> HttpResponse:
    """Renders template blocks instead of whole template for an HTMX request.

    If not an HTMX request (HX-Request is not `true`) will render the entire template.

    If `target` is provided, will also try to match the HX-Target header.

    A list of the blocks rendered is added to template context as `use_blocks`.
    """

    response = TemplateResponse(request, template_name, context, **response_kwargs)

    if (
        request.htmx
        and use_blocks
        and (target is None or target == request.htmx.target)
    ):
        context = (response.context_data or {}) | {"use_blocks": use_blocks}
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
            headers=response.headers,
            status=response.status_code,
        )
    return response
