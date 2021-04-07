from django.utils.functional import SimpleLazyObject, cached_property


class RedirectException(Exception):
    def __init__(self, response, *args, **kwargs):
        self.response = response
        super().__init__(*args, **kwargs)


class RedirectExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, RedirectException):
            return exception.response
        return None


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


class SearchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.search = SimpleLazyObject(lambda: Search(request))
        return self.get_response(request)
