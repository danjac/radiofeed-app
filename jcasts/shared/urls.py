from django.urls import include, path

from jcasts.shared.views import home_page, robots, static_page

about_urls = [
    path(
        "",
        static_page,
        name="credits",
        kwargs={"template_name": "about/credits.html"},
    ),
    path(
        "shortcuts/",
        static_page,
        name="shortcuts",
        kwargs={"template_name": "about/shortcuts.html"},
    ),
    path(
        "privacy/",
        static_page,
        name="privacy",
        kwargs={"template_name": "about/privacy.html"},
    ),
]

error_urls = [
    path(
        "400/",
        static_page,
        name="bad_request",
        kwargs={"template_name": "400.html"},
    ),
    path(
        "403/",
        static_page,
        name="forbidden",
        kwargs={"template_name": "403.html"},
    ),
    path(
        "404/",
        static_page,
        name="not_found",
        kwargs={"template_name": "404.html"},
    ),
    path(
        "405/",
        static_page,
        name="not_allowed",
        kwargs={"template_name": "405.html"},
    ),
    path(
        "500/",
        static_page,
        name="server_error",
        kwargs={"template_name": "500.html"},
    ),
    path(
        "csrf/",
        static_page,
        name="csrf",
        kwargs={"template_name": "403_csrf.html"},
    ),
]

urlpatterns = [
    path("", home_page, name="home_page"),
    path("robots.txt", robots, name="robots"),
    path("about/", include((about_urls, "about"), namespace="about")),
    path("error/", include((error_urls, "error"), namespace="error")),
]
