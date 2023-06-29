import dataclasses
import http

from django.forms import Form
from django.http import HttpRequest


@dataclasses.dataclass(frozen=True)
class Result:
    """Result of form process."""

    is_bound: bool = False
    is_valid: bool = False

    def __bool__(self) -> bool:
        """Returns `True` if form processed and validated."""
        return self.is_bound and self.is_valid

    @property
    def status(self) -> http.HTTPStatus:
        """Return HTTP status based on result."""
        if self.is_bound and not self.is_valid:
            return http.HTTPStatus.UNPROCESSABLE_ENTITY
        return http.HTTPStatus.OK


def handle_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> tuple[Form, Result]:
    """Shortcut for processing form.

    If HTTP POST will pass request data to constructor and validate form, otherwise just initializes unbound form.

    `form_kwargs` will be passed to the form constructor in either case.
    """

    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return form, Result(is_bound=True, is_valid=form.is_valid())

    return form_class(**form_kwargs), Result()
