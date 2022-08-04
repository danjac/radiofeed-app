from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps import views as sitemaps_views
from django.urls import include, path
from django.views.decorators.cache import cache_page

from radiofeed.episodes.sitemaps import EpisodeSitemap
from radiofeed.podcasts.sitemaps import CategorySitemap, PodcastSitemap

sitemaps = {
    "categories": CategorySitemap,
    "episodes": EpisodeSitemap,
    "podcasts": PodcastSitemap,
}


admin.site.site_header = settings.ADMIN_SITE_HEADER


urlpatterns = [
    path("", include("radiofeed.common.urls")),
    path("", include("radiofeed.episodes.urls")),
    path("", include("radiofeed.podcasts.urls")),
    path("", include("radiofeed.users.urls")),
    path(
        "sitemap.xml",
        cache_page(settings.DEFAULT_CACHE_TIMEOUT)(sitemaps_views.index),
        {"sitemaps": sitemaps, "sitemap_url_name": "sitemaps"},
        name="sitemap",
    ),
    path(
        "sitemap-<section>.xml",
        cache_page(settings.DEFAULT_CACHE_TIMEOUT)(sitemaps_views.sitemap),
        {"sitemaps": sitemaps},
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
