import dataclasses

from django.forms import Form
from django.http import HttpRequest


@dataclasses.dataclass(frozen=True, kw_only=True)
class FormResult:
    """Result of form handling."""

    form: Form
    success: bool = False
    processed: bool = False

    def __bool__(self) -> bool:
        """Returns `True` if form is valid."""

        return self.processed and self.success


def handle_form(
    request: HttpRequest, form_class: type[Form], **form_kwargs
) -> FormResult:
    """Handles common form boilerplate. Processes form on HTTP POST and returns result of validation."""

    if request.method == "POST":
        form = form_class(request.POST, request.FILES, **form_kwargs)
        return FormResult(form=form, processed=True, success=form.is_valid())

    return FormResult(form=form_class(**form_kwargs))
