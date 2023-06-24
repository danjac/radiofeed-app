from django.forms import Form
from django.http import HttpRequest


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
