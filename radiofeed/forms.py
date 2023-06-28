import dataclasses
import http

from django.forms import Form
from django.http import HttpRequest


@dataclasses.dataclass(frozen=True)
class FormResult:
    """Result from form handler."""

    form: Form

    is_bound: bool = False
    is_valid: bool = False

    def __bool__(self) -> bool:
        """Returns `True` if valid bound form."""
        return self.is_bound and self.is_valid

    @property
    def status(self) -> http.HTTPStatus:
        """Returns status based on state: 422 if invalid, otherwise 200."""
        return (
            http.HTTPStatus.UNPROCESSABLE_ENTITY
            if self.is_bound and not self.is_valid
            else http.HTTPStatus.OK
        )


def handle_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> FormResult:
    """Shortcut for common form view processing logic.

    If HTTP POST, passes request data to form constructor and validates form.

    If HTTP GET, initializes an unbound form.

    In either case, `form_kwargs` are passed to the form constructor, for example `instance`.

    Returns the form instance and `True` if HTTP POST and valid.
    """

    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return FormResult(form=form, is_bound=True, is_valid=form.is_valid())
    return FormResult(form=form_class(**form_kwargs))
