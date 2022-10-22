from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from render_block import render_block_to_string


def render_block_to_response(
    request: HttpRequest,
    template_name: str,
    block_name: str,
    context: dict | None = None,
    **response_kwargs,
):
    """Render template block into HTTP response."""
    return HttpResponse(
        render_block_to_string(
            template_name,
            block_name,
            context or {},
            request,
        ),
        **response_kwargs,
    )
