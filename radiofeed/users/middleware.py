from radiofeed.common.middleware import BaseMiddleware


from django.conf import settings
from django.http import HttpRequest, HttpResponse


class LanguageMiddleware(BaseMiddleware):
    """Sets language based on user setting."""

    def __call__(self, request: HttpRequest) -> HttpResponse:

        response = self.get_response(request)
        if request.user.is_authenticated:
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, request.user.language)

        return response
