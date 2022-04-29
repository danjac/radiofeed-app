from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps import views as sitemaps_views
from django.urls import include, path
from django.views.decorators.cache import cache_page

from podtracker.episodes.sitemaps import EpisodeSitemap
from podtracker.podcasts.sitemaps import CategorySitemap, PodcastSitemap

sitemaps = {
    "categories": CategorySitemap,
    "episodes": EpisodeSitemap,
    "podcasts": PodcastSitemap,
}


admin.site.site_header = settings.ADMIN_SITE_HEADER


urlpatterns = [
    path("", include("podtracker.common.urls")),
    path("", include("podtracker.episodes.urls")),
    path("", include("podtracker.podcasts.urls")),
    path("", include("podtracker.users.urls")),
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
    path("rq/", include("django_rq.urls")),
    path("ht/", include("health_check.urls")),
    path(settings.ADMIN_URL + "/postgres-metrics/", include("postgres_metrics.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
]

if "debug_toolbar" in settings.INSTALLED_APPS:  # pragma: no cover

    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
