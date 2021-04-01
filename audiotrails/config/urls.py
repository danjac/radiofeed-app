from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps import views as sitemaps_views
from django.template.response import TemplateResponse
from django.urls import include, path
from django.views.decorators.cache import cache_page

from audiotrails.episodes.sitemaps import EpisodeSitemap
from audiotrails.podcasts.sitemaps import CategorySitemap, PodcastSitemap
from audiotrails.users.views import accept_cookies, toggle_dark_mode

sitemaps = {
    "categories": CategorySitemap,
    "episodes": EpisodeSitemap,
    "podcasts": PodcastSitemap,
}


def static_page(template_name):
    return lambda request: TemplateResponse(request, template_name)


@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def robots(request):
    return TemplateResponse(
        request,
        "robots.txt",
        {"sitemap_url": request.build_absolute_uri("/sitemap.xml")},
    )


urlpatterns = [
    path("", include("audiotrails.episodes.urls")),
    path("", include("audiotrails.podcasts.urls")),
    path("account/", include("audiotrails.users.urls")),
    path("accept-cookies/", accept_cookies, name="accept_cookies"),
    path("toggle-dark-mode/", toggle_dark_mode, name="toggle_dark_mode"),
    path("about/", static_page("about.html"), name="about"),
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
