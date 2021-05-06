def search(request):
    return {
        "search": str(request.search),
        "search_qs": "?" + request.search.qs if request.search.qs else "",
    }


def is_cookies_accepted(request):
    return {"accept_cookies": "accept-cookies" in request.COOKIES}
