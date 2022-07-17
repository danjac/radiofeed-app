from __future__ import annotations

from django.shortcuts import render
from django.urls import include, path
from django.views.decorators.http import require_http_methods

from radiofeed.common import views

_static_page = require_http_methods("GET")(render)

about_urls = [
    path(
        "faq/",
        _static_page,
        name="faq",
        kwargs={
            "template_name": "about/faq.html",
        },
    ),
    path(
        "credits/",
        _static_page,
        name="credits",
        kwargs={
            "template_name": "about/credits.html",
        },
    ),
    path(
        "shortcuts/",
        _static_page,
        name="shortcuts",
        kwargs={"template_name": "about/shortcuts.html"},
    ),
    path(
        "terms/",
        _static_page,
        name="terms",
        kwargs={
            "template_name": "about/terms.html",
        },
    ),
]

error_urls = [
    path(
        "400/",
        _static_page,
        name="bad_request",
        kwargs={"template_name": "400.html"},
    ),
    path(
        "403/",
        _static_page,
        name="forbidden",
        kwargs={"template_name": "403.html"},
    ),
    path(
        "404/",
        _static_page,
        name="not_found",
        kwargs={"template_name": "404.html"},
    ),
    path(
        "405/",
        _static_page,
        name="not_allowed",
        kwargs={"template_name": "405.html"},
    ),
    path(
        "500/",
        _static_page,
        name="server_error",
        kwargs={"template_name": "500.html"},
    ),
    path(
        "csrf/",
        _static_page,
        name="csrf",
        kwargs={"template_name": "403_csrf.html"},
    ),
]

urlpatterns = [
    path("about/", include((about_urls, "about"), namespace="about")),
    path("error/", include((error_urls, "error"), namespace="error")),
    path("accept-cookies/", views.accept_cookies, name="accept_cookies"),
    path("robots.txt", views.robots, name="robots"),
    path("favicon.ico", views.favicon, name="favicon"),
    path(".well-known/security.txt", views.security, name="security"),
]
