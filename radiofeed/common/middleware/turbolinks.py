# Django
from django.http import HttpResponse


class TurbolinksMiddleware:
    """
    This provides backend Django complement to the Turbolinks JS framework:

    https://github.com/turbolinks/turbolinks

    In particular redirects are handled correctly as per the documentation.
    """

    session_key = "_turbolinks_redirect"
    location_header = "Turbolinks-Location"
    referrer_header = "Turbolinks-Referrer"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        response = self.get_response(request)
        if response.status_code in (301, 302) and response.has_header("Location"):
            return self.handle_redirect(request, response, response["Location"])
        if response.status_code in range(200, 299):
            location = request.session.pop(self.session_key, None)
            if location:
                response[self.location_header] = location
        return response

    def handle_redirect(self, request, response, location):
        if self.is_turbolinks_request(request):
            return self.redirect_with_turbolinks(request, response, location)
        request.session[self.session_key] = location
        return response

    def is_turbolinks_request(self, request):
        return request.is_ajax() and self.referrer_header in request.headers

    def redirect_with_turbolinks(self, request, response, location):
        js = []
        if request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            js.append("Turbolinks.clearCache();")
        js.append(f"Turbolinks.visit('{location}');")
        js_response = HttpResponse("\n".join(js), content_type="text/javascript")
        # make sure we pass down any cookies e.g. for handling messages
        for k, v in response.cookies.items():
            js_response.set_cookie(k, v)
        js_response["X-Xhr-Redirect"] = location
        return js_response
