from __future__ import annotations

from django.urls import include, path

from radiofeed.common import views

error_urls = [
    path(
        "400/",
        views.static_page,
        name="bad_request",
        kwargs={"template_name": "400.html"},
    ),
    path(
        "403/",
        views.static_page,
        name="forbidden",
        kwargs={"template_name": "403.html"},
    ),
    path(
        "404/",
        views.static_page,
        name="not_found",
        kwargs={"template_name": "404.html"},
    ),
    path(
        "405/",
        views.static_page,
        name="not_allowed",
        kwargs={"template_name": "405.html"},
    ),
    path(
        "500/",
        views.static_page,
        name="server_error",
        kwargs={"template_name": "500.html"},
    ),
    path(
        "csrf/",
        views.static_page,
        name="csrf",
        kwargs={"template_name": "403_csrf.html"},
    ),
]

urlpatterns = [
    path(
        "about/",
        views.static_page,
        name="about",
        kwargs={"template_name": "about.html"},
    ),
    path("accept-cookies/", views.accept_cookies, name="accept_cookies"),
    path("robots.txt", views.robots, name="robots"),
    path("favicon.ico", views.favicon, name="favicon"),
    path(".well-known/security.txt", views.security, name="security"),
    path("error/", include((error_urls, "error"), namespace="error")),
]
