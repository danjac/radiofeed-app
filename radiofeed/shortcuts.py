import dataclasses
from typing import Type

from django.forms import Form
from django.http import HttpRequest


@dataclasses.dataclass
class FormResult:
    form: Form
    is_valid: bool = False

    def __bool__(self) -> bool:
        return self.is_valid


def handle_form(
    request: HttpRequest,
    form_class: Type[Form],
    use_request: bool = False,
    **form_kwargs
) -> FormResult:
    if use_request:
        form_kwargs["request"] = request

    if request.method in ("POST", "PUT"):
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return FormResult(form, form.is_valid())

    return FormResult(form_class(**form_kwargs))
