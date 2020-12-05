class AjaxRequestFragmentMiddleware:
    """Checks for the X-Request-Fragment header passed in AJAX query,
    and sets boolean attribute request.is_ajax_fragment.

    This header is set by the ajax controller when using "replace":
    <div data-controller="ajax"
         data-ajax-replace>
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.is_ajax_fragment = (
            request.is_ajax() and "X-Request-Fragment" in request.headers
        )
        return self.get_response(request)
