import datetime
import io

import requests
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.signing import BadSignature, Signer
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.template.defaultfilters import truncatechars
from django.template.response import TemplateResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.http import require_POST, require_safe
from PIL import Image

from radiofeed.template import COVER_IMAGE_SIZES

_cache_control = cache_control(max_age=60 * 60 * 24, immutable=True)
_cache_page = cache_page(60 * 60)


@require_safe
def about_page(request: HttpRequest) -> TemplateResponse:
    """Renders about page."""
    return TemplateResponse(
        request,
        "about.html",
        {
            "contact_email": settings.CONTACT_EMAIL,
        },
    )


@require_safe
def health_check(request: HttpRequest) -> HttpResponse:
    """Simple ping to check uptime."""
    return HttpResponse("OK")


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
def manifest(request: HttpRequest) -> JsonResponse:
    """PWA manifest.json file."""
    start_url = reverse("podcasts:landing_page")
    theme_color = "#26323C"

    site = Site.objects.get_current()

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
            "name": site.name,
            "short_name": truncatechars(site.name, 12),
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
def cover_image(request: HttpRequest, size: int) -> FileResponse:
    """Proxies a cover image from remote source.

    URL should be signed, so we can verify the request comes from this site.
    """
    # only specific image sizes permitted
    if size not in COVER_IMAGE_SIZES:
        raise Http404

    # check cover url is legit
    try:
        cover_url = Signer().unsign(request.GET["url"])
    except (KeyError, BadSignature) as e:
        raise Http404 from e

    try:
        response = requests.get(
            cover_url,
            headers={
                "User-Agent": settings.USER_AGENT,
            },
            allow_redirects=True,
            timeout=5,
        )

        response.raise_for_status()

        image = Image.open(io.BytesIO(response.content)).resize(
            (size, size),
            Image.Resampling.LANCZOS,
        )

        output = io.BytesIO()
        image.save(output, format="webp", optimize=True, quality=90)
        output.seek(0)

    except (OSError, requests.RequestException):
        # if error we should return a placeholder, so we don't keep
        # trying to fetch and process a bad image instead of caching result

        output = (
            settings.BASE_DIR / "static" / "img" / f"placeholder-{size}.webp"
        ).open("rb")

    return FileResponse(output, content_type="image/webp")
