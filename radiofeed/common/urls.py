from __future__ import annotations

from django.conf import settings
from django.urls import include, path

from radiofeed.common import views

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
]

if settings.DEBUG_ERROR_PAGES:
    urlpatterns += [
        path(
            "error/",
            include(
                (
                    [
                        path(
                            url,
                            views.static_page,
                            name=name,
                            kwargs={"template_name": template_name},
                        )
                        for url, name, template_name in (
                            ("400/", "bad_request", "400.html"),
                            ("403/", "forbidden", "403.html"),
                            ("404/", "not_found", "404.html"),
                            ("405/", "not_allowed", "405.html"),
                            ("500/", "server_error", "500.html"),
                            ("csrf/", "csrf_error", "403_csrf.html"),
                        )
                    ],
                    "error",
                ),
                namespace="error",
            ),
        )
    ]
