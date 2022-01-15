from __future__ import annotations

import datetime

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from jcasts.shared.http import HttpResponseNoContent


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


@require_http_methods(["GET", "HEAD"])
@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def robots_txt(request: HttpRequest) -> HttpResponse:
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
@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def security_txt(request):
    return HttpResponse(
        "\n".join(
            [
                f"Contact: mailto:{settings.CONTACT_DETAILS['email']}",
            ]
        ),
        content_type="text/plain",
    )
