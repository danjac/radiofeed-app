import datetime

from django.conf import settings
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from jcasts.shared.response import HttpResponseNoContent


@require_http_methods(["GET", "HEAD"])
@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def robots(request):
    return TemplateResponse(
        request,
        "robots.txt",
        {"sitemap_url": request.build_absolute_uri("/sitemap.xml")},
    )


@require_http_methods(["GET"])
def health_check(request):
    return HttpResponseNoContent()


@require_http_methods(["POST"])
def accept_cookies(request):
    response = HttpResponse()
    response.set_cookie(
        "accept-cookies",
        value="true",
        expires=timezone.now() + datetime.timedelta(days=30),
        secure=True,
        httponly=True,
        samesite="Lax",
    )
    return response


@require_http_methods(["GET"])
def static_page(request, template_name, extra_context=None):
    return TemplateResponse(request, template_name, extra_context)
