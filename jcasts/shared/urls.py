from django.conf import settings
from django.urls import include, path

from jcasts.shared import views

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
            "extra_context": {"privacy_details": settings.PRIVACY_DETAILS},
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

well_known_urls = [
    path(
        "security.txt",
        views.security_txt,
        name="security_txt",
    )
]

urlpatterns = [
    path("robots.txt", views.robots, name="robots"),
    path("~accept_cookies", views.accept_cookies, name="accept_cookies"),
    path("health/", views.health_check, name="health_check"),
    path("about/", include((about_urls, "about"), namespace="about")),
    path("error/", include((error_urls, "error"), namespace="error")),
    path(
        ".well-known/", include((well_known_urls, "well_known"), namespace="well_known")
    ),
]
