from django.forms import Form
from django.http import HttpRequest


def process_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> tuple[Form, bool]:
    """Shortcut for common form view processing logic.

    If HTTP POST, passes request data to form constructor and validates form.

    If HTTP GET, initializes an unbound form.

    In either case, `form_kwargs` are passed to the form constructor, for example `instance`.

    Returns the form instance and `True` if HTTP POST and valid.
    """

    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return form, form.is_valid()
    return form_class(**form_kwargs), False
