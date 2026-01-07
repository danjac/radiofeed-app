from django.urls import include, path

from simplecasts import views

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
    path("", include("simplecasts.urls.episodes")),
    path("", include("simplecasts.urls.podcasts")),
    path("", include("simplecasts.urls.users")),
]
