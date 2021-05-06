import urllib

from django.utils.functional import SimpleLazyObject, cached_property


class BaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


class Search:
    search_param = "q"

    def __init__(self, request):
        self.request = request

    def __str__(self):
        return self.value

    def __bool__(self):
        return bool(self.value)

    @cached_property
    def value(self):
        return self.request.GET.get(self.search_param, "").strip()

    @cached_property
    def qs(self):
        return (
            urllib.parse.urlencode({self.search_param: self.value})
            if self.value
            else ""
        )


class SearchMiddleware(BaseMiddleware):
    def __call__(self, request):
        request.search = SimpleLazyObject(lambda: Search(request))
        return self.get_response(request)


# adapted from https://raw.githubusercontent.com/adamchainz/django-htmx/main/src/django_htmx/middleware.py
# when django-htmx gets a release, this can be removed.


class HtmxDetails:
    def __init__(self, request):
        self.request = request

    def __bool__(self):
        return self.is_htmx_request

    @cached_property
    def is_htmx_request(self):
        return self.request.headers.get("HX-Request", "") == "true"

    @cached_property
    def current_url(self):
        return self.request.headers.get("HX-Current-URL") or None

    @cached_property
    def prompt(self):
        return self.request.headers.get("HX-Prompt") or None

    @cached_property
    def target(self):
        return self.request.headers.get("HX-Target") or None

    @cached_property
    def trigger(self):
        return self.request.headers.get("HX-Trigger") or None

    @cached_property
    def trigger_name(self):
        return self.request.headers.get("HX-Trigger-Name") or None


class HtmxMiddleware(BaseMiddleware):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.htmx = SimpleLazyObject(lambda: HtmxDetails(request))
        return self.get_response(request)
