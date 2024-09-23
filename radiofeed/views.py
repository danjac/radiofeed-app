import datetime
import functools
import io
from collections.abc import Iterator
from typing import Final

import httpx
from django.conf import settings
from django.core.signing import BadSignature, Signer
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.template.defaultfilters import truncatechars
from django.template.response import TemplateResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.http import require_POST, require_safe
from PIL import Image

from radiofeed.cover_image import get_placeholder_path, is_cover_image_size
from radiofeed.http import HttpRequest
from radiofeed.http_client import get_client

_CACHE_TIMEOUT: Final = 60 * 60 * 24 * 365


_cache_control = cache_control(max_age=_CACHE_TIMEOUT, immutable=True, public=True)
_cache_page = cache_page(_CACHE_TIMEOUT)


@require_safe
def index(request) -> HttpResponseRedirect | TemplateResponse:
    """Landing page of site."""

    # if user logged in, redirect to their home page
    if request.user.is_authenticated:
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
    return TemplateResponse(request, "index.html")


@require_safe
def about(request: HttpRequest) -> TemplateResponse:
    """Renders About page."""
    return TemplateResponse(
        request,
        "about.html",
        {
            "contact_email": settings.CONTACT_EMAIL,
        },
    )


@require_safe
def privacy(request: HttpRequest) -> TemplateResponse:
    """Renders Privacy page."""
    return TemplateResponse(request, "privacy.html")


@require_POST
def accept_gdpr_cookies(_) -> HttpResponse:
    """Handles "accept" action on GDPR cookie banner."""
    response = HttpResponse()
    response.set_cookie(
        settings.GDPR_COOKIE_NAME,
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
def favicon(_) -> FileResponse:
    """Generates favicon file."""
    return FileResponse((settings.STATIC_SRC / "img" / "wave-ico.png").open("rb"))


@require_safe
@_cache_control
@_cache_page
def service_worker(request: HttpRequest) -> TemplateResponse:
    """PWA service worker."""
    return TemplateResponse(
        request,
        "service_worker.js",
        content_type="application/javascript",
    )


@require_safe
@_cache_control
@_cache_page
def assetlinks(request: HttpRequest) -> JsonResponse:
    """PWA assetlinks"""

    package_name = settings.PWA_CONFIG["assetlinks"]["package_name"]
    fingerprints = settings.PWA_CONFIG["assetlinks"]["sha256_fingerprints"]

    return JsonResponse(
        [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": package_name,
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        ],
        safe=False,
    )


@require_safe
@_cache_control
@_cache_page
def manifest(request: HttpRequest) -> JsonResponse:
    """PWA manifest.json file."""
    start_url = reverse("index")

    categories = settings.PWA_CONFIG["manifest"]["categories"]
    description = settings.PWA_CONFIG["manifest"]["description"]
    background_color = settings.PWA_CONFIG["manifest"]["background_color"]
    theme_color = settings.PWA_CONFIG["manifest"]["theme_color"]

    return JsonResponse(
        {
            "background_color": background_color,
            "theme_color": theme_color,
            "description": description,
            "dir": "ltr",
            "display": "minimal-ui",
            "name": request.site.name,
            "short_name": truncatechars(request.site.name, 12),
            "prefer_related_applications": False,
            "orientation": "any",
            "scope": start_url,
            "start_url": start_url,
            "id": "?homescreen=1",
            "display_override": [
                "minimal-ui",
                "window-controls-overlay",
            ],
            "launch_handler": {
                "client_mode": [
                    "focus-existing",
                    "auto",
                ]
            },
            "categories": categories,
            "screenshots": [
                {
                    "src": static("img/desktop.png"),
                    "label": "Desktop homescreen",
                    "form_factor": "wide",
                    "type": "image/png",
                },
                {
                    "src": static("img/mobile.png"),
                    "label": "Mobile homescreen",
                    "form_factor": "narrow",
                    "type": "image/png",
                },
            ],
            "icons": _app_icons_list(),
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
                        "/bookmarks/",
                        "/categories/",
                        "/discover/",
                        "/episodes/",
                        "/history/",
                        "/new/",
                        "/podcasts/",
                        "/private-feeds/",
                        "/search/",
                        "/subscriptions/",
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
def cover_image(request: HttpRequest, size: int) -> FileResponse:
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

        image = Image.open(io.BytesIO(response.content)).resize(
            (size, size),
            Image.Resampling.LANCZOS,
        )

        output = io.BytesIO()
        image.save(output, format="webp", optimize=True, quality=90)
        output.seek(0)

    except (OSError, httpx.HTTPError, httpx.StreamError):
        # if error we should return a placeholder, so we don't keep
        # trying to fetch and process a bad image instead of caching result

        output = get_placeholder_path(size).open("rb")

    return FileResponse(output, content_type="image/webp")


@functools.cache
def _app_icons_list() -> list[dict]:
    return list(_app_icons())


def _app_icons() -> Iterator[dict]:
    icons = [
        {"src": "android/android-launchericon-512-512.png", "sizes": "512x512"},
        {"src": "android/android-launchericon-192-192.png", "sizes": "192x192"},
        {"src": "android/android-launchericon-144-144.png", "sizes": "144x144"},
        {"src": "android/android-launchericon-96-96.png", "sizes": "96x96"},
        {"src": "android/android-launchericon-72-72.png", "sizes": "72x72"},
        {"src": "android/android-launchericon-48-48.png", "sizes": "48x48"},
        {"src": "ios/16.png", "sizes": "16x16"},
        {"src": "ios/20.png", "sizes": "20x20"},
        {"src": "ios/29.png", "sizes": "29x29"},
        {"src": "ios/32.png", "sizes": "32x32"},
        {"src": "ios/40.png", "sizes": "40x40"},
        {"src": "ios/50.png", "sizes": "50x50"},
        {"src": "ios/57.png", "sizes": "57x57"},
        {"src": "ios/58.png", "sizes": "58x58"},
        {"src": "ios/60.png", "sizes": "60x60"},
        {"src": "ios/64.png", "sizes": "64x64"},
        {"src": "ios/72.png", "sizes": "72x72"},
        {"src": "ios/76.png", "sizes": "76x76"},
        {"src": "ios/80.png", "sizes": "80x80"},
        {"src": "ios/87.png", "sizes": "87x87"},
        {"src": "ios/100.png", "sizes": "100x100"},
        {"src": "ios/114.png", "sizes": "114x114"},
        {"src": "ios/120.png", "sizes": "120x120"},
        {"src": "ios/128.png", "sizes": "128x128"},
        {"src": "ios/144.png", "sizes": "144x144"},
        {"src": "ios/152.png", "sizes": "152x152"},
        {"src": "ios/167.png", "sizes": "167x167"},
        {"src": "ios/180.png", "sizes": "180x180"},
        {"src": "ios/192.png", "sizes": "192x192"},
        {"src": "ios/256.png", "sizes": "256x256"},
        {"src": "ios/512.png", "sizes": "512x512"},
        {"src": "ios/1024.png", "sizes": "1024x1024"},
    ]
    for icon in icons:
        app_icon = icon | {
            "src": static(f"img/icons/{icon['src']}"),
            "type": "image/png",
        }
        yield app_icon
        yield app_icon | {"purpose": "maskable"}
        yield app_icon | {"purpose": "any"}
