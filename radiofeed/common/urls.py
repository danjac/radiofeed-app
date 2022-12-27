from __future__ import annotations

from django.conf import settings
from django.urls import path

from radiofeed.common import views

urlpatterns = [
    path(
        "about/",
        views.static_page,
        name="about",
        kwargs={
            "template_name": "about.html",
            "extra_context": {
                "contact_email": settings.CONTACT_EMAIL,
            },
        },
    ),
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
]
