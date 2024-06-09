import functools
import pathlib
import urllib.parse
from enum import StrEnum
from typing import Final

from django.conf import settings
from django.core.signing import Signer
from django.http import HttpRequest
from django.templatetags.static import static
from django.urls import reverse

_COVER_IMAGE_SIZES: Final = (96, 120, 240)


class CoverImageSize(StrEnum):
    """Possible size variations."""

    SMALL = "sm"
    LARGE = "lg"


_COVER_IMAGE_VARIANTS = {
    CoverImageSize.SMALL: (96, 96),
    CoverImageSize.LARGE: (120, 240),
}


@functools.cache
def get_cover_image_attrs(cover_url: str, size: CoverImageSize) -> dict:
    """Returns the HTML attributes for an image."""
    min_size, full_size = _COVER_IMAGE_VARIANTS[size]

    full_src = get_cover_image_url(cover_url, full_size)

    attrs = {
        "height": full_size,
        "width": full_size,
        "src": full_src,
    }

    # one size only
    if min_size == full_size:
        return attrs

    min_src = get_cover_image_url(cover_url, min_size)

    srcset = ", ".join(
        [
            f"{full_src} {full_size}w",
            f"{min_src} {min_size}w",
        ]
    )

    sizes = ", ".join(
        [
            f"(max-width: 767.99px){min_size}px",
            f"(min-width: 768px) {full_size}px",
        ]
    )

    return attrs | {"srcset": srcset, "sizes": sizes}


@functools.cache
def get_cover_image_url(cover_url: str | None, size: int) -> str:
    """Return the cover image URL"""
    return (
        (
            reverse(
                "cover",
                kwargs={
                    "size": size,
                },
            )
            + "?"
            + urllib.parse.urlencode({"url": Signer().sign(cover_url)})
        )
        if cover_url
        else get_placeholder_url(size)
    )


@functools.cache
def get_placeholder(size: int) -> str:
    """Return placeholder image name"""
    return f"placeholder-{size}.webp"


@functools.cache
def get_placeholder_url(size: int) -> str:
    """Return URL to cover image placeholder"""
    return static(f"img/{get_placeholder(size)}")


@functools.cache
def get_placeholder_path(size: int) -> pathlib.Path:
    """Returns path to placeholder image"""
    return settings.BASE_DIR / "static" / "img" / get_placeholder(size)


def is_cover_image_size(size: int) -> bool:
    """Check image has correct size."""
    return size in _COVER_IMAGE_SIZES


def get_metadata_info(request: HttpRequest, cover_url: str | None) -> list[dict]:
    """Returns media artwork details."""
    return [
        {
            "src": request.build_absolute_uri(get_cover_image_url(cover_url, size)),
            "sizes": f"{size}x{size}",
            "type": "image/webp",
        }
        for size in _COVER_IMAGE_SIZES
    ]
