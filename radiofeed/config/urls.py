from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps import views as sitemaps_views
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from radiofeed.episodes.sitemaps import EpisodeSitemap
from radiofeed.podcasts.sitemaps import CategorySitemap, PodcastSitemap
from radiofeed.users.views import accept_cookies, confirm_new_user_cta, toggle_dark_mode

sitemaps = {
    "categories": CategorySitemap,
    "episodes": EpisodeSitemap,
    "podcasts": PodcastSitemap,
}


SITEMAPS_CACHE_TIMEOUT = 3600

urlpatterns = [
    path("", include("radiofeed.episodes.urls")),
    path("", include("radiofeed.podcasts.urls")),
    path("account/", include("radiofeed.users.urls")),
    path("accept-cookies/", accept_cookies, name="accept_cookies"),
    path("confirm-new-user-cta/", confirm_new_user_cta, name="confirm_new_user_cta"),
    path("toggle-dark-mode/", toggle_dark_mode, name="toggle_dark_mode"),
    path("about/", TemplateView.as_view(template_name="about.html"), name="about"),
    path(settings.ADMIN_URL, admin.site.urls),
    path(
        "sitemap.xml",
        cache_page(SITEMAPS_CACHE_TIMEOUT)(sitemaps_views.index),
        {"sitemaps": sitemaps, "sitemap_url_name": "sitemaps"},
    ),
    path(
        "sitemap-<section>.xml",
        cache_page(SITEMAPS_CACHE_TIMEOUT)(sitemaps_views.sitemap),
        {"sitemaps": sitemaps},
        name="sitemaps",
    ),
]


if settings.DEBUG:

    if "silk" in settings.INSTALLED_APPS:
        urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

    # static views
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # allow preview/debugging of error views in development
    urlpatterns += [
        path("errors/400/", TemplateView.as_view(template_name="400.html")),
        path("errors/403/", TemplateView.as_view(template_name="403.html")),
        path("errors/404/", TemplateView.as_view(template_name="404.html")),
        path("errors/405/", TemplateView.as_view(template_name="405.html")),
        path("errors/500/", TemplateView.as_view(template_name="500.html")),
        path("errors/csrf/", TemplateView.as_view(template_name="403_csrf.html")),
    ]
