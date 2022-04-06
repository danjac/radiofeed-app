import contextlib

from typing import Generator, Type

from django.forms import Form
from django.http import HttpRequest


@contextlib.contextmanager
def handle_form(
    request: HttpRequest, form_class: Type[Form], **form_kwargs
) -> Generator[tuple[Form, bool], None, None]:
    if request.method == "POST":
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        yield form, form.is_valid()
    else:
        yield form_class(**form_kwargs), False
