import datetime
import functools
import io
import itertools
from collections.abc import Iterator
from typing import Final, TypedDict

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


class Icon(TypedDict):
    """PWA icon info."""

    src: str
    sizes: str


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
    for icon in itertools.chain(_android_icons(), _ios_icons()):
        app_icon = icon | {
            "src": static(f"img/icons/{icon.src}"),
            "type": "image/png",
        }
        yield app_icon
        yield app_icon | {"purpose": "maskable"}
        yield app_icon | {"purpose": "any"}


def _android_icons() -> Iterator[Icon]:
    for size in (
        512,
        192,
        144,
        96,
        72,
        48,
    ):
        yield Icon(
            src=f"src-android/android-launchericon-{size}-{size}.png",
            sizes=f"{size}x{size}",
        )


def _ios_icons() -> Iterator[Icon]:
    for size in (
        16,
        20,
        29,
        32,
        40,
        50,
        57,
        58,
        60,
        64,
        72,
        76,
        80,
        97,
        100,
        114,
        120,
        128,
        144,
        152,
        167,
        180,
        192,
        256,
        512,
        1024,
    ):
        yield Icon(
            src=f"ios/{size}.png",
            sizes=f"{size}x{size}",
        )
