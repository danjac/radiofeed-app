from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from health_check.views import HealthCheckView

from radiofeed import views

urlpatterns = [
    path("", views.index, name="index"),
    path("about/", views.about, name="about"),
    path("privacy/", views.privacy, name="privacy"),
    path("accept-cookies/", views.accept_cookies, name="accept_cookies"),
    path(
        "covers/<int:size>/<str:encoded_url>.webp",
        views.cover_image,
        name="cover_image",
    ),
    path("robots.txt", views.robots, name="robots"),
    path("manifest.json", views.manifest, name="manifest"),
    path(".well-known/assetlinks.json", views.assetlinks, name="assetlinks"),
    path(".well-known/security.txt", views.security, name="security"),
    path("", include("radiofeed.episodes.urls")),
    path("", include("radiofeed.podcasts.urls")),
    path("", include("radiofeed.users.urls")),
    path("account/", include("allauth.urls")),
    # "live" check that the app is running, without doing any expensive checks
    path(
        "ht/ping/",
        HealthCheckView.as_view(
            checks=[
                "radiofeed.health_checks.SimplePingHealthCheck",
            ]
        ),
    ),
    # "ready" check that does more expensive checks to ensure the app is ready to serve traffic
    path(
        "ht/",
        HealthCheckView.as_view(
            checks=[
                "health_check.Cache",
                "health_check.Database",
                "health_check.contrib.redis.Redis",
            ]
        ),
    ),
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
