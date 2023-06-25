import http

from django.forms import Form
from django.http import HttpRequest


def handle_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> tuple[Form, bool, http.HTTPStatus]:
    """Shortcut for form processing logic.

    On HTTP POST will initialize form class with request data, otherwise creates unbound form with `**form_kwargs`.

    Returns form instance and `True` if bound form is valid, along with the HTTP status (422 if form is invalid, otherwise 200).
    """

    if request.method == "POST":
        form = form_class(request.POST, request.FILES, **form_kwargs)
        is_valid = form.is_valid()
        return (
            form,
            is_valid,
            http.HTTPStatus.OK if is_valid else http.HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    return form_class(**form_kwargs), False, http.HTTPStatus.OK
