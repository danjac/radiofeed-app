from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from health_check.views import HealthCheckView

urlpatterns = [
    # Project URLs
    path("", include("radiofeed.urls")),
    path("", include("radiofeed.episodes.urls")),
    path("", include("radiofeed.podcasts.urls")),
    path("", include("radiofeed.users.urls")),
    # Django Allauth URLs for authentication
    path("account/", include("allauth.urls")),
    # Health check endpoints
    # "live" check that the app is running, without doing any expensive checks
    path(
        "ht/live/",
        HealthCheckView.as_view(checks=["health_check.DNS"]),
        name="health_check_live",
    ),
    # "ready" check that does more expensive checks to ensure the app is ready to serve traffic
    path(
        "ht/ready/",
        HealthCheckView.as_view(
            checks=[
                "health_check.Cache",
                "health_check.Database",
            ]
        ),
        name="health_check_ready",
    ),
    # Django admin site
    path(settings.ADMIN_URL, admin.site.urls),
]

# Development-only URLs for local tooling


if "django_browser_reload" in settings.INSTALLED_APPS:  # pragma: no cover
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]

if "debug_toolbar" in settings.INSTALLED_APPS:  # pragma: no cover
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]
