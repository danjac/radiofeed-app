from __future__ import annotations

import datetime
import io

from typing import Final

import httpx

from django.conf import settings
from django.core.signing import BadSignature, Signer
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.http import require_POST, require_safe
from PIL import Image

from radiofeed.common.user_agent import user_agent

_DEFAULT_CACHE_TIMEOUT: Final = 3600  # one hour


_cache_control = cache_control(max_age=_DEFAULT_CACHE_TIMEOUT, immutable=True)
_cache_page = cache_page(_DEFAULT_CACHE_TIMEOUT)


@require_safe
def about_page(request: HttpRequest) -> HttpResponse:
    """Renders about page."""
    return render(request, "about.html", {"contact_email": settings.CONTACT_EMAIL})


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
@_cache_control
@_cache_page
def favicon(request: HttpRequest) -> FileResponse:
    """Generates favicon file."""
    return FileResponse(
        (settings.BASE_DIR / "static" / "img" / "wave-ico.png").open("rb")
    )


@require_safe
@_cache_control
@_cache_page
def service_worker(request: HttpRequest) -> HttpResponse:
    """PWA service worker."""
    return render(request, "service_worker.js", content_type="application/javascript")


@require_safe
@_cache_control
@_cache_page
def manifest(request: HttpRequest) -> HttpResponse:
    """PWA manifest.json file."""
    start_url = reverse("podcasts:landing_page")
    theme_color = "#26323C"

    icon = {
        "src": static("img/wave.png"),
        "type": "image/png",
        "sizes": "512x512",
    }

    return JsonResponse(
        {
            "background_color": theme_color,
            "theme_color": theme_color,
            "description": "Podcast aggregator site",
            "dir": "ltr",
            "display": "standalone",
            "name": "Radiofeed",
            "short_name": "Radiofeed",
            "orientation": "any",
            "scope": start_url,
            "start_url": start_url,
            "categories": [
                "books",
                "education",
                "entertainment",
                "news",
                "politics",
                "sport",
            ],
            "screenshots": [
                static("img/desktop.png"),
                static("img/mobile.png"),
            ],
            "icons": [
                icon,
                {**icon, "purpose": "any"},
                {**icon, "purpose": "maskable"},
            ],
            "shortcuts": [],
            "lang": "en",
        }
    )


@require_safe
@_cache_control
@_cache_page
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
                        "/categories/",
                        "/episodes/",
                        "/history/",
                        "/podcasts/",
                    ]
                ],
            ]
        ),
        content_type="text/plain",
    )


@require_safe
@_cache_control
@_cache_page
def security(request: HttpRequest) -> HttpResponse:
    """Generates security.txt file containing contact details etc."""
    return HttpResponse(
        "\n".join(
            [
                f"Contact: mailto:{settings.CONTACT_EMAIL}",
            ]
        ),
        content_type="text/plain",
    )


@require_safe
@_cache_control
@_cache_page
def cover_image(request: HttpRequest, size: int) -> HttpResponse:
    """Proxies a cover image from remote source."""
    # only certain range of sizes permitted
    if size not in (100, 200, 300):
        raise Http404

    # check cover url is legit
    try:
        cover_url = Signer().unsign(request.GET["url"])
    except (KeyError, BadSignature):
        raise Http404

    try:
        response = httpx.get(
            cover_url,
            follow_redirects=True,
            timeout=5,
            headers={
                "User-Agent": user_agent(),
            },
        )

        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content)).resize(
            (size, size),
            Image.Resampling.LANCZOS,
        )

        output = io.BytesIO()
        image.save(output, format="webp", optimize=True, quality=90)
        output.seek(0)

    except (OSError, httpx.HTTPError):
        # if error we should return a placeholder, so we don't keep
        # trying to fetch and process a bad image instead of caching result

        output = (
            settings.BASE_DIR / "static" / "img" / f"placeholder-{size}.webp"
        ).open("rb")

    return FileResponse(output, content_type="image/webp")
