from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("listenwave.urls")),
    path("", include("listenwave.episodes.urls")),
    path("", include("listenwave.podcasts.urls")),
    path("", include("listenwave.users.urls")),
    path("account/", include("allauth.urls")),
    path("ht/", include("health_check.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
]


if "django_browser_reload" in settings.INSTALLED_APPS:  # pragma: no cover
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]

if "debug_toolbar" in settings.INSTALLED_APPS:  # pragma: no cover
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
