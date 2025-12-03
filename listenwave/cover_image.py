import contextlib
import functools
import io
import itertools
import pathlib
from collections.abc import Generator
from typing import BinaryIO, Final, Literal

import httpx
from django.conf import settings
from django.core.signing import BadSignature, Signer
from django.http import HttpRequest
from django.templatetags.static import static
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from PIL import Image

from listenwave.client import Client
from listenwave.pwa import ImageInfo

CoverImageVariant = Literal["card", "detail", "tile"]


_COVER_IMAGE_MAX_SIZE = 12 * 1024 * 1024  # 12 MB

_COVER_IMAGE_SIZES: Final[dict[CoverImageVariant, tuple[int, int]]] = {
    "card": (96, 96),
    "detail": (144, 160),
    "tile": (160, 224),
}

_COMPRESSION_RATIOS: Final[dict[str, float]] = {
    "jpeg": 16.0,
    "jpg": 16.0,
    "webp": 12.0,
    "png": 25.0,
    "gif": 15.0,
    "bmp": 1.0,
    "tiff": 2.0,
}

_BYTES_PER_PIXEL: Final[dict[str, float]] = {
    "RGB": 3,
    "RGBA": 4,
    "L": 1,
    "P": 1,
    "CMYK": 4,
    "1": 0.125,
    "I": 4,
    "F": 4,
}


class URLSigner(Signer):
    """Custom URL signer with shortened signature."""

    max_length: int = 6

    def signature(self, value: str | bytes, key: str | bytes | None = None) -> str:
        """Truncate signature to max_length."""
        full_signature = super().signature(value, key)
        return full_signature[-self.max_length :]


class CoverImageError(Exception):
    """Base class for cover image fetching errors."""


class CoverImageFetchError(CoverImageError):
    """Raised when the cover image cannot be fetched."""


class CoverImageInvalidError(CoverImageError):
    """Raised when the cover image is invalid."""


class CoverImageDecryptionError(CoverImageError):
    """Raised when the cover image cannot be decrypted."""


class CoverImageSaveError(CoverImageError):
    """Raised when the cover image cannot be saved."""


class CoverImageTooLargeError(CoverImageError):
    """Raised when the cover image exceeds the maximum allowed size."""


def get_cover_image_attrs(
    variant: CoverImageVariant,
    cover_url: str | None,
    title: str,
) -> dict:
    """Returns the HTML attributes for an image."""

    classes = " ".join(("cover", "border", variant))
    min_size, full_size = _COVER_IMAGE_SIZES[variant]
    full_src = get_cover_image_url(cover_url, full_size)

    attrs = {
        "alt": title,
        "aria_hidden": "true",
        "class": classes,
        "decoding": "async",
        "height": full_size,
        "loading": "lazy",
        "src": full_src,
        "title": title,
        "width": full_size,
    }

    # no size variations
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
            f"(max-width: 1023.99px) {min_size}px",
            f"(min-width: 1024px) {full_size}px",
        ]
    )

    return attrs | {"srcset": srcset, "sizes": sizes}


def fetch_cover_image(
    client: Client,
    cover_url: str,
    size: int,
) -> Image.Image:
    """Fetches the cover image, resizing to the specified size.
    Raises CoverImageError if the image is too large or cannot be fetched or processed.
    """

    try:
        response = client.head(cover_url)

        try:
            content_length = int(response.headers.get("Content-Length", 0))
        except ValueError:
            content_length = 0

        if content_length > _COVER_IMAGE_MAX_SIZE:
            raise CoverImageTooLargeError

        with _handle_output_stream(io.BytesIO()) as output:
            with client.stream(cover_url) as response:
                for chunk in response.iter_bytes():
                    output.write(chunk)
                    if output.tell() > _COVER_IMAGE_MAX_SIZE:
                        raise CoverImageTooLargeError

            image = Image.open(output)
            width, height = image.size

            if (width * height) > get_max_pixels(image.format, image.mode):
                raise CoverImageTooLargeError

            return image.resize((size, size), Image.Resampling.LANCZOS)
    except httpx.HTTPError as exc:
        raise CoverImageFetchError from exc
    except (
        Image.UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
    ) as exc:
        raise CoverImageInvalidError from exc


def save_cover_image(
    image: Image.Image,
    *,
    output: BinaryIO | None = None,
    format: str = "webp",
    quality: float = 90,
) -> BinaryIO:
    """Saves image to the output stream."""
    try:
        with _handle_output_stream(output or io.BytesIO()) as rv:
            image.save(rv, format=format, quality=quality, optimize=True)
            return rv
    except OSError as exc:
        raise CoverImageSaveError from exc


def get_metadata_info(request: HttpRequest, cover_url: str) -> list[ImageInfo]:
    """Returns media artwork details."""
    return [
        ImageInfo(
            src=request.build_absolute_uri(get_cover_image_url(cover_url, size)),
            sizes=f"{size}x{size}",
            type="image/webp",
        )
        for size in get_cover_image_sizes()
    ]


@functools.lru_cache(maxsize=512)
def get_cover_image_url(cover_url: str | None, size: int) -> str:
    """Return the cover image URL"""
    return (
        reverse(
            "cover_image",
            kwargs={
                "encoded_url": encode_cover_url(cover_url),
                "size": size,
            },
        )
        if cover_url
        else get_placeholder_url(size)
    )


@functools.lru_cache(maxsize=2048)
def encode_cover_url(cover_url: str) -> str:
    """Returns signed cover URL"""
    signed_url = get_cover_url_signer().sign(cover_url)
    return urlsafe_base64_encode(signed_url.encode())


@functools.lru_cache(maxsize=2048)
def decode_cover_url(encoded_url: str) -> str:
    """Returns unsigned cover URL"""
    try:
        signed_url = urlsafe_base64_decode(encoded_url).decode()
        return get_cover_url_signer().unsign(signed_url)
    except (BadSignature, ValueError, TypeError) as exc:
        raise CoverImageDecryptionError from exc


@functools.cache
def get_max_pixels(format: str, mode: str) -> int:
    """Returns max pixels based on estimated compression ratio and bytes per pixel"""
    compression_ratio = _COMPRESSION_RATIOS.get(format.lower(), 3.0)
    bytes_per_pixel = _BYTES_PER_PIXEL.get(mode.upper(), 3.0)

    return int((_COVER_IMAGE_MAX_SIZE * compression_ratio) / bytes_per_pixel)


@functools.cache
def is_cover_image_size(size: int) -> bool:
    """Check image has correct size."""
    return size in get_cover_image_sizes()


@functools.lru_cache(maxsize=64)
def get_cover_image_sizes() -> set[int]:
    """Returns set of allowed sizes."""
    return set(itertools.chain.from_iterable(_COVER_IMAGE_SIZES.values()))


@functools.lru_cache(maxsize=16)
def get_placeholder(size: int) -> str:
    """Return placeholder image name"""
    return f"placeholder-{size}.webp"


@functools.lru_cache(maxsize=16)
def get_placeholder_url(size: int) -> str:
    """Return URL to cover image placeholder"""
    return static(f"img/placeholders/{get_placeholder(size)}")


@functools.lru_cache(maxsize=16)
def get_placeholder_path(size: int) -> pathlib.Path:
    """Returns path to placeholder image"""
    return settings.STATIC_SRC / "img" / "placeholders" / get_placeholder(size)


@functools.cache
def get_cover_url_signer() -> Signer:
    """Return URL signer"""
    return URLSigner(salt="cover_url")


@contextlib.contextmanager
def _handle_output_stream(output: BinaryIO) -> Generator[BinaryIO]:
    yield output
    output.truncate()
    output.seek(0)
