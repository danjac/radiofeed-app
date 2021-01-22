# Standard Library
import functools

# Django
from django.utils.functional import SimpleLazyObject


class Search:
    search_param = "q"

    def __init__(self, request):
        self.request = request

    @functools.lru_cache
    def __str__(self):
        return self.request.GET.get(self.search_param, "")

    def __bool__(self):
        return bool(str(self))


class SearchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.search = SimpleLazyObject(lambda: Search(request))
        return self.get_response(request)
