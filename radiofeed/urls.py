from __future__ import annotations

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = settings.ADMIN_SITE_HEADER

urlpatterns = [
    path("", include("radiofeed.common.urls")),
    path("", include("radiofeed.episodes.urls")),
    path("", include("radiofeed.podcasts.urls")),
    path("", include("radiofeed.users.urls")),
    path("account/", include("allauth.urls")),
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
