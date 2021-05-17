from django.http import HttpRequest


def search(request: HttpRequest) -> dict[str, str]:
    return {
        "search": str(request.search),
        "search_qs": "?" + request.search.qs if request.search.qs else "",
    }


def is_cookies_accepted(request: HttpRequest) -> dict[str, bool]:
    return {"accept_cookies": "accept-cookies" in request.COOKIES}
