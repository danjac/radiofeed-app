from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from radiofeed.fragments import render_template_fragments


def handle_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> tuple[Form, bool]:
    """Shortcut for processing a Django form.

    If POST request, initializes form with request data and calls `is_valid()`. Otherwise returns unbound form.

    Returns the initialized form and `True` or `False` if form is valid.
    """
    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return form, form.is_valid()
    return form_class(**form_kwargs), False


def render_form_response(
    request: HttpRequest,
    form: Form,
    template_name: str,
    extra_context: dict | None = None,
    *,
    form_target: str = "form",
    form_context_name: str = "form",
    use_blocks: list[str] | None = None,
    **response_kwargs,
) -> HttpResponse:
    """
    Renders a form.

    If using HTMX, will try to render the form block only if matching target name.
    """

    context = (extra_context or {}) | {form_context_name: form}
    use_blocks = use_blocks or ["form"]

    if request.htmx.target == form_target:
        return render_template_fragments(
            request,
            template_name,
            context,
            use_blocks=use_blocks,
            **response_kwargs,
        )
    return render(request, template_name, context, **response_kwargs)
