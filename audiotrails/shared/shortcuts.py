from django.http import HttpResponse
from django.shortcuts import redirect, resolve_url


def hx_redirect(request, to, *args, permanent=False, **kwargs):
    if request.htmx:
        response = HttpResponse()
        response["HX-Redirect"] = resolve_url(to, *args, **kwargs)
        return response
    return redirect(to, *args, permanent=permanent, **kwargs)
