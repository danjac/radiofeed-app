from django.conf import settings
from django.http import HttpRequest, HttpResponse

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request: HttpRequest) -> HttpResponse:
        return settings.HOME_URL
