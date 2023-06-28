import dataclasses
import http

from django.forms import Form
from django.http import HttpRequest


@dataclasses.dataclass(frozen=True)
class FormResult:
    """Result of form processing."""

    form: Form

    is_bound: bool = False
    is_valid: bool = False

    def __bool__(self) -> bool:
        """Returns `True` if form processed and validated."""
        return self.is_bound and self.is_valid

    @property
    def status(self) -> http.HTTPStatus:
        """Returns HTTP status of result.

        If validation failed, returns 422 UNPROCESSABLE ENTITY, otherwise 200 OK.
        """
        return (
            http.HTTPStatus.UNPROCESSABLE_ENTITY
            if self.is_bound and not self.is_valid
            else http.HTTPStatus.OK
        )


def process_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> FormResult:
    """Handles form validation if HTTP POST.
    Any arguments in `form_kwargs` are passed to Form constructor for both GET and POST.
    """

    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return FormResult(form=form, is_bound=True, is_valid=form.is_valid())
    return FormResult(form=form_class(**form_kwargs))
