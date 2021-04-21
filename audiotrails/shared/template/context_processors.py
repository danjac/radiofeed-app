def search(request):
    return {"search": request.search}


def is_cookies_accepted(request):
    return {"accept_cookies": "accept-cookies" in request.COOKIES}
