import datetime

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from jcasts.shared.response import HttpResponseNoContent


@require_http_methods(["GET", "HEAD"])
@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def robots(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "robots.txt",
        {"sitemap_url": request.build_absolute_uri("/sitemap.xml")},
    )


@require_http_methods(["GET"])
def health_check(request: HttpRequest) -> HttpResponse:
    return HttpResponseNoContent()


@require_http_methods(["POST"])
def accept_cookies(request: HttpRequest) -> HttpResponse:
    response = HttpResponseNoContent()
    response.set_cookie(
        "accept-cookies",
        value="true",
        expires=timezone.now() + datetime.timedelta(days=365),
        secure=True,
        httponly=True,
        samesite="Lax",
    )
    return response


@require_http_methods(["GET"])
def static_page(
    request: HttpRequest, template_name: str, extra_context: dict | None = None
) -> HttpResponse:
    return TemplateResponse(request, template_name, extra_context)
