from django.forms import Form
from django.http import HttpRequest


def handle_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> tuple[Form, bool]:
    """Handles form validation if HTTP POST, returning form instance and `True` if valid.

    If not POST, returns form instance and `False`.

    Any arguments in `form_kwargs` are passed to Form constructor for both GET and POST.
    """

    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return form, form.is_valid()
    return form_class(**form_kwargs), False
