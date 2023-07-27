import dataclasses

from django.forms import Form
from django.http import HttpRequest


@dataclasses.dataclass(frozen=True)
class FormResult:
    """Result of `handle_form`."""

    is_bound: bool = False
    is_valid: bool = False

    @property
    def success(self) -> bool:
        """Returns `True` if form is bound and valid."""
        return self.is_bound and self.is_valid

    @property
    def status(self) -> int:
        """Return HTTP status based on form result."""
        return 422 if self.is_bound and not self.is_valid else 200


def handle_form(
    form_class: type[Form], request: HttpRequest, **form_kwargs
) -> tuple[Form, FormResult]:
    """Shortcut for processing form.

    If HTTP POST will pass request data to constructor and validate form, otherwise just initializes unbound form.

    `form_kwargs` will be passed to the form constructor in either case.
    """

    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return form, FormResult(is_bound=True, is_valid=form.is_valid())

    return form_class(**form_kwargs), FormResult()
