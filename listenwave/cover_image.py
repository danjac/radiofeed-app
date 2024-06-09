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

_COVER_IMAGE_SIZES: Final = (
    96,
    128,
    160,
    192,
    224,
)


class CoverImageSize(StrEnum):
    """Possible size variations."""

    SMALL = "sm"
    MEDIUM = "md"
    LARGE = "lg"


_COVER_IMAGE_INFO = {
    CoverImageSize.SMALL: (96, 96),
    CoverImageSize.MEDIUM: (128, 160),
    CoverImageSize.LARGE: (192, 224),
}


def is_cover_image_size(size: int) -> bool:
    """Check image has correct size."""
    return size in _COVER_IMAGE_SIZES


@functools.cache
def get_cover_image_attrs(cover_url: str, variant: CoverImageSize) -> dict[str, str]:
    """Returns the HTML attributes for an image."""
    min_size, full_size = _COVER_IMAGE_INFO[variant]
    full_size_src = get_cover_image_url(cover_url, full_size)

    attrs = {
        "height": full_size,
        "width": full_size,
        "src": full_size_src,
    }

    # one size only
    if min_size == full_size:
        return attrs

    srcset = ", ".join(
        [
            f"{full_size_src} {full_size}w",
            f"{get_cover_image_url(cover_url, min_size)} {min_size}w",
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
                "cover_image",
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
def get_placeholder_url(size: int) -> str:
    """Return URL to cover image placeholder"""
    return static(f"img/placeholder-{size}.webp")


@functools.cache
def get_placeholder_path(size: int) -> pathlib.Path:
    """Returns path to placeholder image"""
    return settings.BASE_DIR / "static" / "img" / f"placeholder-{size}.webp"


def get_metadata_info(request: HttpRequest, cover_url: str) -> dict[str, str]:
    """Returns media artwork details."""
    return [
        {
            "src": request.build_absolute_uri(
                get_cover_image_url(cover_url, info["default_size"])
                if cover_url
                else get_placeholder_url(size)
            ),
            "sizes": f"{[info["default_size"]]}x{info["default_size"]}",
            "type": "image/webp",
        }
        for size, info in _COVER_IMAGE_INFO.items()
    ]
