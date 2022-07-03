from urllib.parse import urlencode

from django.utils.encoding import force_str
from django.utils.functional import SimpleLazyObject, cached_property


class BaseMiddleware:
    """Convenient base class for custom middleware.

    Args:
        get_response (Callable): callable taking HTTP request/response
    """

    def __init__(self, get_response):
        self.get_response = get_response


class Search:
    """Encapsulates generic search query.

    Attributes:
        search_param (str): query string parameter
    Args:
        request (HttpRequest)
    """

    search_param = "q"

    def __init__(self, request):
        self.request = request

    def __str__(self):
        """Returns search query value.

        Returns:
            str
        """
        return self.value

    def __bool__(self):
        """Returns `True` if search in query and has a non-empty value.

        Returns:
            bool
        """
        return bool(self.value)

    @cached_property
    def value(self):
        """Returns the search query value, if any.

        Returns:
            str
        """
        return force_str(self.request.GET.get(self.search_param, "")).strip()

    @cached_property
    def qs(self):
        """Returns encoded query string value, if any.

        Returns:
            str
        """
        return urlencode({self.search_param: self.value}) if self.value else ""


class SearchMiddleware(BaseMiddleware):
    """Adds Search instance to the request as `request.search`."""

    def __call__(self, request):
        """Resolves middleware.

        Args:
            request (HttpRequest)

        Returns:
            HttpResponse
        """
        request.search = SimpleLazyObject(lambda: Search(request))
        return self.get_response(request)


class CacheControlMiddleware(BaseMiddleware):
    """Workaround for https://github.com/bigskysoftware/htmx/issues/497.

    Place after HtmxMiddleware
    """

    def __call__(self, request):
        """Resolves middleware.

        Args:
            request (HttpRequest)

        Returns:
            HttpResponse
        """
        response = self.get_response(request)
        if request.htmx:
            # don't override if cache explicitly set
            response.setdefault("Cache-Control", "no-store, max-age=0")
        return response
