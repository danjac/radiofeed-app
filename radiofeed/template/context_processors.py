from typing import Dict

from django.conf import settings
from django.http import HttpRequest


def search(request: HttpRequest) -> Dict:
    return {"search": request.search}


def google_tracking_id(request: HttpRequest) -> Dict:
    return {"google_tracking_id": getattr(settings, "GOOGLE_TRACKING_ID", None)}


def is_cookies_accepted(request: HttpRequest) -> Dict:
    return {"accept_cookies": "accept-cookies" in request.COOKIES}


def is_dark_mode(request: HttpRequest) -> Dict:
    return {"dark_mode": "dark-mode" in request.COOKIES}


def show_new_user_cta(request: HttpRequest) -> Dict:
    return {
        "show_new_user_cta": request.user.is_anonymous
        and "new-user-cta" not in request.COOKIES
    }
