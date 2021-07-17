from typing import Callable

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps import views as sitemaps_views
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_safe

from jcasts.episodes.sitemaps import EpisodeSitemap
from jcasts.podcasts.sitemaps import CategorySitemap, PodcastSitemap
from jcasts.users.views import accept_cookies

sitemaps = {
    "categories": CategorySitemap,
    "episodes": EpisodeSitemap,
    "podcasts": PodcastSitemap,
}


@require_safe
def home_page(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("episodes:index")
    return TemplateResponse(request, "index.html")


def static_page(template_name: str) -> Callable:
    @require_safe
    def _render_page(request: HttpRequest):
        return TemplateResponse(request, template_name)

    return _render_page


@require_safe
@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def robots(request: HttpRequest) -> HttpResponse:
    return TemplateResponse(
        request,
        "robots.txt",
        {"sitemap_url": request.build_absolute_uri("/sitemap.xml")},
    )


about_urls = [
    path(
        "",
        static_page("about/credits.html"),
        name="credits",
    ),
    path(
        "shortcuts/",
        static_page("about/shortcuts.html"),
        name="shortcuts",
    ),
    path(
        "privacy/",
        static_page("about/privacy.html"),
        name="privacy",
    ),
]

urlpatterns = [
    path("", home_page, name="home_page"),
    path("", include("jcasts.episodes.urls")),
    path("", include("jcasts.podcasts.urls")),
    path("account/", include("jcasts.users.urls")),
    path("about/", include((about_urls, "about"), namespace="about")),
    path("accept-cookies/", accept_cookies, name="accept_cookies"),
    path("robots.txt", robots, name="robots"),
    path(
        "sitemap.xml",
        cache_page(settings.DEFAULT_CACHE_TIMEOUT)(sitemaps_views.index),
        {"sitemaps": sitemaps, "sitemap_url_name": "sitemaps"},
    ),
    path(
        "sitemap-<section>.xml",
        cache_page(settings.DEFAULT_CACHE_TIMEOUT)(sitemaps_views.sitemap),
        {"sitemaps": sitemaps},
        name="sitemaps",
    ),
    path(settings.ADMIN_URL, admin.site.urls),
]


if settings.DEBUG:

    if "silk" in settings.INSTALLED_APPS:
        urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

    # static views
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # allow preview/debugging of error views in development
    urlpatterns += [
        path("errors/400/", static_page("400.html")),
        path("errors/403/", static_page("403.html")),
        path("errors/404/", static_page("404.html")),
        path("errors/405/", static_page("405.html")),
        path("errors/500/", static_page("500.html")),
        path("errors/csrf/", static_page("403_csrf.html")),
    ]
