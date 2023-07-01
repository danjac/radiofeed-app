from django.forms import Form
from django.http import HttpRequest


def handle_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> tuple[Form, bool]:
    """Shortcut for processing form.

    If HTTP POST will pass request data to constructor and validate form, otherwise just initializes unbound form.

    `form_kwargs` will be passed to the form constructor in either case.

    Returns the form instance and `True` if form is valid.

    If form takes `request` as an argument, pass in as `_request` e.g.

        handle_form(MyForm, request, _request=request)
    """

    if _request := form_kwargs.pop("_request", None):
        form_kwargs["request"] = _request

    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return form, form.is_valid()

    return form_class(**form_kwargs), False
