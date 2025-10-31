import dataclasses
from typing import Any, Protocol

from django.http import HttpRequest


class FormProtocol(Protocol):
    """Protocol representing the essential methods of a Django Form."""

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def is_valid(self) -> bool: ...  # noqa: D102


@dataclasses.dataclass(kw_only=True, frozen=True)
class FormResult:
    """Dataclass representing the result of a form processing operation."""

    form: FormProtocol

    is_valid: bool = False
    is_submitted: bool = False

    def __bool__(self) -> bool:
        """Returns True if the form was submitted + valid, False otherwise."""
        return self.is_submitted and self.is_valid


def handle_form(
    form_class: type[FormProtocol],
    request: HttpRequest,
    **form_kwargs,
) -> FormResult:
    """
    Processes a Django form and returns a FormResult indicating a successful submission.
    """
    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return FormResult(form=form, is_submitted=True, is_valid=form.is_valid())
    return FormResult(form=form_class(**form_kwargs))
