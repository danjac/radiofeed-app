from __future__ import annotations

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from radiofeed import views

admin.site.site_header = settings.ADMIN_SITE_HEADER


urlpatterns = [
    path("", include("radiofeed.episodes.urls")),
    path("", include("radiofeed.podcasts.urls")),
    path("", include("radiofeed.users.urls")),
    path("account/", include("allauth.urls")),
    path("about/", views.about_page, name="about"),
    path("accept-cookies/", views.accept_cookies, name="accept_cookies"),
    path(
        "covers/<str:encoded_url>/<int:size>/cover.webp",
        views.cover_image,
        name="cover_image",
    ),
    path("robots.txt", views.robots, name="robots"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("manifest.json", views.manifest, name="manifest"),
    path("favicon.ico", views.favicon, name="favicon"),
    path(".well-known/security.txt", views.security, name="security"),
    path(settings.ADMIN_URL, admin.site.urls),
]

if apps.is_installed("debug_toolbar"):  # pragma: no cover
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]


if apps.is_installed("django_browser_reload"):  # pragma: no cover
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
