import dataclasses

from django.forms import Form
from django.http import HttpRequest


@dataclasses.dataclass(frozen=True, kw_only=True)
class FormResult:
    """Captures result of form processing."""

    form: Form
    success: bool = False
    processed: bool = False

    def __bool__(self) -> bool:
        """Returns `True` if form has been successfully processed and validated."""

        return self.processed and self.success


def handle_form(
    request: HttpRequest, form_class: type[Form], **form_kwargs
) -> FormResult:
    """Initializes a form and handles form validation if POST or PUT."""

    if request.method in ("POST", "PUT"):
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return FormResult(form=form, processed=True, success=form.is_valid())

    return FormResult(form=form_class(**form_kwargs))
