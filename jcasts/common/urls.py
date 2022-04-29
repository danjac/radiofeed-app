from django.urls import include, path

from jcasts.common import views

about_urls = [
    path(
        "faq/",
        views.static_page,
        name="faq",
        kwargs={
            "template_name": "about/faq.html",
        },
    ),
    path(
        "credits/",
        views.static_page,
        name="credits",
        kwargs={
            "template_name": "about/credits.html",
        },
    ),
    path(
        "shortcuts/",
        views.static_page,
        name="shortcuts",
        kwargs={"template_name": "about/shortcuts.html"},
    ),
    path(
        "terms/",
        views.static_page,
        name="terms",
        kwargs={
            "template_name": "about/terms.html",
        },
    ),
]

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
    path("about/", include((about_urls, "about"), namespace="about")),
    path("error/", include((error_urls, "error"), namespace="error")),
    path("accept-cookies/", views.accept_cookies, name="accept_cookies"),
    path("robots.txt", views.robots, name="robots"),
    path("favicon.ico", views.favicon, name="favicon"),
    path(".well-known/security.txt", views.security, name="security"),
]
