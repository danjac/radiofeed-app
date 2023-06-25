from django.forms import Form
from django.http import HttpRequest


def handle_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> tuple[Form, bool]:
    """
    Shortcut to handle form

    On HTTP POST, returns form and `True` if form is valid, else False.
    """

    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return form, form.is_valid()
    return form_class(**form_kwargs), False
