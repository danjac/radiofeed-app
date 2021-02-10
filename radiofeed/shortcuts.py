import contextlib
from typing import Generator, Tuple, Type

from django.forms import Form
from django.http import HttpRequest


@contextlib.contextmanager
def handle_form(
    request: HttpRequest, form_class: Type[Form], **form_kwargs
) -> Generator[Tuple[Form, bool], None, None]:
    # in case form has "request" as arg
    if "_request" in form_kwargs:
        form_kwargs["request"] = form_kwargs.pop("_request")
    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        yield form, form.is_valid()
    else:
        yield form_class(**form_kwargs), False
