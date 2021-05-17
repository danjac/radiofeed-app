from typing import Dict

from django.http import HttpRequest


def search(request: HttpRequest) -> Dict[str, str]:
    return {
        "search": str(request.search),
        "search_qs": "?" + request.search.qs if request.search.qs else "",
    }


def is_cookies_accepted(request: HttpRequest) -> Dict[str, bool]:
    return {"accept_cookies": "accept-cookies" in request.COOKIES}
