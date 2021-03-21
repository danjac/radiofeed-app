from django.conf import settings


def search(request):
    return {"search": request.search}


def google_tracking_id(request):
    return {"google_tracking_id": getattr(settings, "GOOGLE_TRACKING_ID", None)}


def is_cookies_accepted(request):
    return {"accept_cookies": "accept-cookies" in request.COOKIES}


def is_dark_mode(request):
    return {"dark_mode": "dark-mode" in request.COOKIES}
