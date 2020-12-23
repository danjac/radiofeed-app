# Django
from django.conf import settings

# Third Party Libraries
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def ajax_response(self, request, response, *args, **kwargs):
        print("AJAX RESPONSE MOFO")
        return response


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        return settings.HOME_URL
