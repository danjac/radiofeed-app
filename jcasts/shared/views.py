from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_safe


@require_safe
def home_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(settings.HOME_URL)
    return TemplateResponse(request, "index.html")


@require_safe
@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def robots(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "robots.txt",
        {"sitemap_url": request.build_absolute_uri("/sitemap.xml")},
    )


@require_safe
def static_page(request: HttpRequest, template_name: str) -> HttpResponse:
    return TemplateResponse(request, template_name)
