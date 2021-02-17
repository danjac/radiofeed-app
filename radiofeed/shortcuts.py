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
    request: HttpRequest, form_class: Type[Form], **form_kwargs
) -> FormResult:
    # in case form has "request" as arg
    if "_request" in form_kwargs:
        form_kwargs["request"] = form_kwargs.pop("_request")
    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return FormResult(form, form.is_valid())
    else:
        return FormResult(form_class(**form_kwargs))
