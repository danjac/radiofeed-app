from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def render_partial_for_target(
    request: HttpRequest,
    template_name: str,
    context: dict | None = None,
    *,
    target: str,
    partial: str,
    **response_kwargs,
) -> HttpResponse:
    """Conditionally renders a template partial if `target` matches the HX-Target header.

    Otherwise renders the full template.
    """
    if request.htmx.target == target:
        template_name += f"#{partial}"

    return render(request, template_name, context, **response_kwargs)
