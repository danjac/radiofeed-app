import datetime
import io
from typing import Final

import httpx
from django.conf import settings
from django.core.signing import BadSignature, Signer
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.http import require_POST, require_safe
from PIL import Image

from radiofeed import pwa
from radiofeed.cover_image import get_placeholder_path, is_cover_image_size
from radiofeed.http_client import get_client

_CACHE_TIMEOUT: Final = 60 * 60 * 24 * 365


_cache_control = cache_control(max_age=_CACHE_TIMEOUT, immutable=True, public=True)
_cache_page = cache_page(_CACHE_TIMEOUT)


@require_safe
def index(request) -> HttpResponse:
    """Landing page of site."""

    # if user logged in, redirect to their home page
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, "index.html")


@require_safe
def about(request: HttpRequest) -> HttpResponse:
    """Renders About page."""
    return render(
        request,
        "about.html",
        {
            "contact_email": settings.CONTACT_EMAIL,
        },
    )


@require_safe
def privacy(request: HttpRequest) -> HttpResponse:
    """Renders Privacy page."""
    return render(request, "privacy.html")


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
def assetlinks(_) -> JsonResponse:
    """PWA assetlinks"""
    return JsonResponse(pwa.get_assetlinks(), safe=False)


@require_safe
@_cache_control
@_cache_page
def manifest(request: HttpRequest) -> JsonResponse:
    """PWA manifest.json file."""
    return JsonResponse(pwa.get_manifest(request))


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
                    f"Allow: {reverse(url_name)}$"
                    for url_name in [
                        "index",
                        "about",
                        "privacy",
                    ]
                ],
                "Disallow: /",
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
