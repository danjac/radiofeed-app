# Django
from django.conf import settings
from django.http import HttpResponseNotAllowed
from django.shortcuts import render


class HttpResponseNotAllowedMiddleware:
    """
    Renders a custom 405 template if settings.DEBUG = False.
    """

    template_name = "405.html"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if isinstance(response, HttpResponseNotAllowed) and not settings.DEBUG:
            return render(request, self.template_name, status=405)
        return response
