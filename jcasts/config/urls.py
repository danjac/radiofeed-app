from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps import views as sitemaps_views
from django.urls import include, path
from django.views.decorators.cache import cache_page

from jcasts.episodes.sitemaps import EpisodeSitemap
from jcasts.podcasts.sitemaps import CategorySitemap, PodcastSitemap
from jcasts.users.views import accept_cookies

sitemaps = {
    "categories": CategorySitemap,
    "episodes": EpisodeSitemap,
    "podcasts": PodcastSitemap,
}


urlpatterns = [
    path("", include("jcasts.shared.urls")),
    path("", include("jcasts.episodes.urls")),
    path("", include("jcasts.podcasts.urls")),
    path("account/", include("jcasts.users.urls")),
    path("accept-cookies/", accept_cookies, name="accept_cookies"),
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
