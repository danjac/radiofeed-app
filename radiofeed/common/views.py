from __future__ import annotations

import datetime

from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.http import require_POST, require_safe

from radiofeed.common.template import get_site_config

static_page = require_safe(render)


@require_POST
def accept_cookies(request: HttpRequest) -> HttpResponse:
    """Handles "accept" action on GDPR cookie banner."""
    response = HttpResponse()
    response.set_cookie(
        "accept-cookies",
        value="true",
        expires=timezone.now() + datetime.timedelta(days=365),
        secure=True,
        httponly=True,
        samesite="Lax",
    )
    return response


@require_safe
@cache_control(max_age=settings.DEFAULT_CACHE_TIMEOUT, immutable=True)
def favicon(request: HttpRequest) -> FileResponse:
    """Generates favicon file."""
    return FileResponse(
        (settings.BASE_DIR / "static" / "img" / "wave-ico.png").open("rb")
    )


@require_safe
@cache_control(max_age=settings.DEFAULT_CACHE_TIMEOUT, immutable=True)
@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def robots(request: HttpRequest) -> HttpResponse:
    """Generates robots.txt file."""
    return HttpResponse(
        "\n".join(
            [
                "User-Agent: *",
                *[
                    f"Disallow: {url}"
                    for url in [
                        "/account/",
                        "/bookmarks/",
                        "/history/",
                    ]
                ],
                f"Sitemap: {request.build_absolute_uri(reverse('sitemap'))}",
            ]
        ),
        content_type="text/plain",
    )


@require_safe
@cache_control(max_age=settings.DEFAULT_CACHE_TIMEOUT, immutable=True)
@cache_page(settings.DEFAULT_CACHE_TIMEOUT)
def security(request: HttpRequest) -> HttpResponse:
    """Generates security.txt file containing contact details etc."""
    return HttpResponse(
        "\n".join(
            [
                f"Contact: mailto:{get_site_config().contact_email}",
            ]
        ),
        content_type="text/plain",
    )
