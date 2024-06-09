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

_MAX_WIDTH_LG: Final = 1525
_MAX_WIDTH_SM: Final = 767

_MIN_WIDTH_MD: Final = 768
_MIN_WIDTH_XL: Final = 1526

_COVER_IMAGE_SIZES: Final = (
    64,
    112,
    128,
    160,
    192,
    224,
)


class Variant(StrEnum):
    """Possible variations"""

    SMALL = "sm"
    MEDIUM = "md"
    LARGE = "lg"


class CoverImageInfo(TypedDict):
    """Specific rendering information for each size."""

    default_size: int
    srcset: list[tuple[int, int]]
    sizes: list[str]


_COVER_IMAGE_INFO = {
    Variant.SMALL: CoverImageInfo(
        default_size=64,
        srcset=[],
        sizes=[],
    ),
    Variant.MEDIUM: CoverImageInfo(
        default_size=160,
        srcset=[
            (128, _MAX_WIDTH_SM),
            (160, _MIN_WIDTH_MD),
        ],
        sizes=[
            f"(min-width {_MIN_WIDTH_MD}) 160px",
            f"(max-width {_MAX_WIDTH_SM}) 128px",
        ],
    ),
    Variant.LARGE: CoverImageInfo(
        default_size=224,
        srcset=[
            (224, _MIN_WIDTH_XL),
            (192, _MAX_WIDTH_LG),
        ],
        sizes=[
            f"(min-width {_MIN_WIDTH_XL}px) 224px",
            f"(max-width {_MAX_WIDTH_LG}px) 192px",
        ],
    ),
}


def is_cover_image_size(size: int) -> bool:
    """Check image has correct size."""
    return size in _COVER_IMAGE_SIZES


@functools.cache
def get_cover_image_attrs(cover_url: str, variant: Variant) -> dict[str, str]:
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
    if not info["srcset"] or not info["sizes"]:
        return attrs | {"size": info["default_size"]}

    srcset = ", ".join(
        [
            f"{get_cover_image_url(cover_url, size)} {width}w"
            for size, width in info["srcset"]
        ]
    )

    sizes = ", ".join(info["sizes"])

    return attrs | {"srcset": srcset, "sizes": sizes}


@functools.cache
def get_placeholder_url(variant: Variant) -> str:
    """Return URL to cover image placeholder"""
    return static(f"img/placeholder-{_COVER_IMAGE_INFO[variant]["default_size"]}.webp")


@functools.cache
def get_placeholder_path(size: int) -> pathlib.Path:
    """Returns path to placeholder image"""
    return settings.BASE_DIR / "static" / "img" / f"placeholder-{size}.webp"


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


def get_artwork_info(request: HttpRequest, cover_url: str) -> dict[str, str]:
    """Returns media artwork details."""
    return [
        {
            "src": request.build_absolute_uri(
                get_cover_image_url(variant)
                if cover_url
                else get_placeholder_url(variant)
            ),
            "sizes": f"{[info["default_size"]]}x{info["default_size"]}",
            "type": "image/webp",
        }
        for variant, info in _COVER_IMAGE_INFO.items()
    ]
