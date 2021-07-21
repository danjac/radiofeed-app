import functools

from django.conf import settings
from django.http import HttpRequest, HttpResponse
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


about_credits = functools.partial(static_page, template_name="about/credit.html")
about_shortcuts = functools.partial(static_page, template_name="about/shortcuts.html")
about_privacy = functools.partial(static_page, template_name="about/privacy.html")
