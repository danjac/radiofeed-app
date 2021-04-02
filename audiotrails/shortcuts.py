from contextlib import contextmanager


@contextmanager
def handle_form(request, form_class, use_request=False, **form_kwargs):
    if use_request:
        form_kwargs["request"] = request
    if request.method in ("POST", "PUT"):
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        yield form, form.is_valid()
    else:
        yield form_class(**form_kwargs), False
