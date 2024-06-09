import datetime
import functools
import io
import pathlib
from typing import Final

import httpx
from django.conf import settings
from django.core.signing import BadSignature, Signer
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.defaultfilters import truncatechars
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.http import require_POST, require_safe
from PIL import Image

from listenwave.cover_image import get_placeholder_path, is_cover_image_size
from listenwave.http_client import get_client
from listenwave.templatetags import ACCEPT_COOKIES_NAME

_PWA_THEME_COLOR: Final = "#26323C"

_cache_control = cache_control(max_age=60 * 60 * 24 * 365, immutable=True)
_cache_page = cache_page(60 * 60)


@require_safe
def about_page(request: HttpRequest) -> HttpResponse:
    """Renders about page."""
    return render(
        request,
        "about.html",
        {
            "contact_email": settings.CONTACT_EMAIL,
        },
    )


@require_POST
def accept_cookies(_) -> HttpResponse:
    """Handles "accept" action on GDPR cookie banner."""
    response = HttpResponse()
    response.set_cookie(
        ACCEPT_COOKIES_NAME,
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
def favicon(_) -> HttpResponse:
    """Generates favicon file."""
    return FileResponse(_favicon_path().open("rb"))


@require_safe
@_cache_control
@_cache_page
def service_worker(request: HttpRequest) -> HttpResponse:
    """PWA service worker."""
    return render(
        request,
        "service_worker.js",
        content_type="application/javascript",
    )


@require_safe
@_cache_control
@_cache_page
def manifest(request: HttpRequest) -> HttpResponse:
    """PWA manifest.json file."""
    start_url = reverse("podcasts:index")

    icon = {
        "src": static("img/wave.png"),
        "type": "image/png",
        "sizes": "512x512",
    }

    return JsonResponse(
        {
            "background_color": _PWA_THEME_COLOR,
            "theme_color": _PWA_THEME_COLOR,
            "description": "Podcast aggregator site",
            "dir": "ltr",
            "display": "standalone",
            "name": request.site.name,
            "short_name": truncatechars(request.site.name, 12),
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
                icon | {"purpose": "maskable"},
                icon | {"purpose": "any"},
            ],
            "shortcuts": [],
            "lang": "en",
        }
    )


@require_safe
@_cache_control
@_cache_page
def robots(_) -> HttpResponse:
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
                        "/discover/",
                        "/episodes/",
                        "/history/",
                        "/podcasts/",
                        "/private-feeds/",
                    ]
                ],
            ]
        ),
        content_type="text/plain",
    )


@require_safe
@_cache_control
@_cache_page
def security(_) -> HttpResponse:
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
def cover(request: HttpRequest, size: int) -> HttpResponse:
    """Proxies a cover image from remote source.

    URL should be signed, so we can verify the request comes from this site.
    """
    # only specific image sizes permitted
    if not is_cover_image_size(size):
        raise Http404

    # check cover url is legit
    try:
        cover_url = Signer().unsign(request.GET["url"])
    except (KeyError, BadSignature) as exc:
        raise Http404 from exc

    output: io.BufferedIOBase

    try:
        response = get_client().get(cover_url)
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

        output = get_placeholder_path(size).open("rb")

    return FileResponse(output, content_type="image/webp")


@functools.cache
def _favicon_path() -> pathlib.Path:
    return settings.BASE_DIR / "static" / "img" / "wave-ico.png"
