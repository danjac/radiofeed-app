import functools
import pathlib
import urllib.parse
from enum import StrEnum
from typing import Final, TypedDict

from django.conf import settings
from django.core.signing import Signer
from django.http import HttpRequest
from django.templatetags.static import static
from django.urls import reverse

_COVER_IMAGE_SIZES: Final = (
    64,
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


class CoverImageInfo(TypedDict):
    """Specific rendering information for each size."""

    default_size: int

    min_size: tuple[int, int]
    max_size: tuple[int, int]


_COVER_IMAGE_INFO = {
    CoverImageSize.SMALL: CoverImageInfo(
        default_size=64,
        min_size=(0, 0),
        max_size=(0, 0),
    ),
    CoverImageSize.MEDIUM: CoverImageInfo(
        default_size=160,
        min_size=(128, 767),
        max_size=(160, 768),
    ),
    CoverImageSize.LARGE: CoverImageInfo(
        default_size=224,
        min_size=(192, 1525),
        max_size=(224, 1526),
    ),
}


def is_cover_image_size(size: int) -> bool:
    """Check image has correct size."""
    return size in _COVER_IMAGE_SIZES


@functools.cache
def get_cover_image_attrs(cover_url: str, variant: CoverImageSize) -> dict[str, str]:
    """Returns the HTML attributes for an image."""
    info = _COVER_IMAGE_INFO[variant]

    attrs = {
        "height": info["default_size"],
        "width": info["default_size"],
    }

    if not cover_url:
        return attrs | {
            "src": get_placeholder_url(info["default_size"]),
        }

    attrs |= {
        "src": get_cover_image_url(cover_url, info["default_size"]),
    }

    # one size only
    if (0, 0) in (info["min_size"], info["max_size"]):
        return attrs | {"size": info["default_size"]}

    srcset = ", ".join(
        [
            f"{get_cover_image_url(cover_url, size)} {width}w"
            for size, width in (
                info["max_size"],
                info["min_size"],
            )
        ]
    )

    sizes = ", ".join(
        [
            f"({attr} {width}px) {size}px"
            for (attr, size, width) in (
                ("min-width", *info["max_size"]),
                ("max-width", *info["min_size"]),
            )
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
        else ""
    )


def get_placeholder_url(variant: CoverImageSize) -> str:
    """Return URL to cover image placeholder"""
    return static(f"img/placeholder-{_COVER_IMAGE_INFO[variant]["default_size"]}.webp")


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
