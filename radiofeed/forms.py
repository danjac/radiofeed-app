import dataclasses
import http

from django.forms import Form
from django.http import HttpRequest


@dataclasses.dataclass(frozen=True)
class FormResult:
    """Form handling result."""

    form: Form
    success: bool = False
    status: http.HTTPStatus = http.HTTPStatus.OK

    def __bool__(self) -> bool:
        """Returns True if success."""
        return self.success


def handle_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> FormResult:
    """Shortcut for form processing logic.

    On HTTP POST will initialize form class with request data, otherwise creates unbound form with `**form_kwargs`.

    Returns form instance and `True` if bound form is valid, along with the HTTP status (422 if form is invalid, otherwise 200).
    """

    if request.method == "POST":
        form = form_class(request.POST, request.FILES, **form_kwargs)
        is_valid = form.is_valid()
        return FormResult(
            form=form,
            success=is_valid,
            status=http.HTTPStatus.OK
            if is_valid
            else http.HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    return FormResult(form=form_class(**form_kwargs))
