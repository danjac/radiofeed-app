from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps import views as sitemaps_views
from django.urls import include, path
from django.views.decorators.cache import cache_page

from radiofeed.common import views
from radiofeed.episodes.sitemaps import EpisodeSitemap
from radiofeed.podcasts.sitemaps import CategorySitemap, PodcastSitemap

_sitemaps = {
    "categories": CategorySitemap,
    "episodes": EpisodeSitemap,
    "podcasts": PodcastSitemap,
}


admin.site.site_header = settings.ADMIN_SITE_HEADER

urlpatterns = [
    path("", include("radiofeed.episodes.urls")),
    path("", include("radiofeed.podcasts.urls")),
    path("", include("radiofeed.users.urls")),
    path(
        "about/",
        views.static_page,
        name="about",
        kwargs={"template_name": "about.html"},
    ),
    path("accept-cookies/", views.accept_cookies, name="accept_cookies"),
    path("robots.txt", views.robots, name="robots"),
    path("favicon.ico", views.favicon, name="favicon"),
    path(".well-known/security.txt", views.security, name="security"),
    path(
        "sitemap.xml",
        cache_page(settings.DEFAULT_CACHE_TIMEOUT)(sitemaps_views.index),
        {"sitemaps": _sitemaps, "sitemap_url_name": "sitemaps"},
        name="sitemap",
    ),
    path(
        "sitemap-<section>.xml",
        cache_page(settings.DEFAULT_CACHE_TIMEOUT)(sitemaps_views.sitemap),
        {"sitemaps": _sitemaps},
        name="sitemaps",
    ),
    path("account/", include("allauth.urls")),
    path(f"{settings.ADMIN_URL}pg-metrics/", include("postgres_metrics.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
]

if "debug_toolbar" in settings.INSTALLED_APPS:  # pragma: no cover
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]

if "silk" in settings.INSTALLED_APPS:  # pragma: no cover
    urlpatterns += [
        path("silk/", include("silk.urls")),
    ]

if settings.DEBUG_ERROR_PAGES:
    urlpatterns += [
        path(
            "error/",
            include(
                (
                    [
                        path(
                            "400/",
                            views.static_page,
                            name="bad_request",
                            kwargs={"template_name": "400.html"},
                        ),
                        path(
                            "403/",
                            views.static_page,
                            name="forbidden",
                            kwargs={"template_name": "403.html"},
                        ),
                        path(
                            "404/",
                            views.static_page,
                            name="not_found",
                            kwargs={"template_name": "404.html"},
                        ),
                        path(
                            "405/",
                            views.static_page,
                            name="not_allowed",
                            kwargs={"template_name": "405.html"},
                        ),
                        path(
                            "500/",
                            views.static_page,
                            name="server_error",
                            kwargs={"template_name": "500.html"},
                        ),
                        path(
                            "csrf/",
                            views.static_page,
                            name="csrf",
                            kwargs={"template_name": "403_csrf.html"},
                        ),
                    ],
                    "error",
                ),
                namespace="error",
            ),
        )
    ]
