from __future__ import annotations

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
    path(f"{settings.ADMIN_URL}pg-metrics/", include("postgres_metrics.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
]

if settings.DEBUG:  # pragma: no cover

    urlpatterns += [
        path("silk/", include("silk.urls")),
        path("__debug__/", include("debug_toolbar.urls")),
        path("__reload__/", include("django_browser_reload.urls")),
    ]
