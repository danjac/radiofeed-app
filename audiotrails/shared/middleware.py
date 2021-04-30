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


class SearchMiddleware(BaseMiddleware):
    def __call__(self, request):
        request.search = SimpleLazyObject(lambda: Search(request))
        return self.get_response(request)
