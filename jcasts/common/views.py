from __future__ import annotations

import datetime

from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.http import require_http_methods

from jcasts.common.http import HttpResponseNoContent

CACHE_TIMEOUT = 24 * 60 * 60


@require_http_methods(["GET"])
def health_check(request: HttpRequest) -> HttpResponse:
    return HttpResponseNoContent()


@require_http_methods(["POST"])
def accept_cookies(request: HttpRequest) -> HttpResponse:
    response = HttpResponseNoContent()
    response.set_cookie(
        "accept-cookies",
        value="true",
        expires=timezone.now() + datetime.timedelta(days=365),
        secure=True,
        httponly=True,
        samesite="Lax",
    )
    return response


@require_http_methods(["GET"])
def static_page(
    request: HttpRequest, template_name: str, extra_context: dict | None = None
) -> HttpResponse:
    return TemplateResponse(request, template_name, extra_context)


@require_http_methods(["GET"])
@cache_control(max_age=CACHE_TIMEOUT, immutable=True)
def favicon(request: HttpRequest) -> HttpResponse:
    return FileResponse(
        (settings.BASE_DIR / "assets" / "img" / "wave-ico.png").open("rb")
    )


@require_http_methods(["GET", "HEAD"])
@cache_control(max_age=CACHE_TIMEOUT, immutable=True)
@cache_page(CACHE_TIMEOUT)
def robots(request: HttpRequest) -> HttpResponse:
    return HttpResponse(
        "\n".join(
            [
                "User-Agent: *",
                *[
                    f"Disallow: {url}"
                    for url in [
                        "/account/",
                        "/favorites/",
                        "/history/",
                    ]
                ],
                f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
            ]
        ),
        content_type="text/plain",
    )


@require_http_methods(["GET"])
@cache_control(max_age=CACHE_TIMEOUT, immutable=True)
@cache_page(CACHE_TIMEOUT)
def security(request):
    return HttpResponse(
        "\n".join(
            [
                f"Contact: mailto:{settings.PROJECT_METADATA['contact_email']}",
            ]
        ),
        content_type="text/plain",
    )
