from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from listenfeed import views

urlpatterns = [
    path("", views.index, name="index"),
    path("", include("listenfeed.episodes.urls")),
    path("", include("listenfeed.podcasts.urls")),
    path("", include("listenfeed.users.urls")),
    path("account/", include("allauth.urls")),
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
