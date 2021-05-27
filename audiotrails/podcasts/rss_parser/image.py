from __future__ import annotations

import io
import mimetypes
import os
import uuid

from urllib.parse import urlparse

import requests

from django.core.files.images import ImageFile
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from audiotrails.podcasts.rss_parser.exceptions import InvalidImageError
from audiotrails.podcasts.rss_parser.http import get_content_type, get_response

MAX_IMAGE_SIZE = 1000
IMAGE_EXTENSIONS = (".jpg", ".png", ".jpeg")


def fetch_image_file_from_url(image_url: str) -> ImageFile | None:

    try:
        response = get_response(image_url)

        return ImageFile(
            create_image_obj(response.content),
            name=create_random_image_filename(
                image_url, get_content_type(image_url, response.headers)
            ),
        )
    except (
        requests.RequestException,
        DecompressionBombError,
        UnidentifiedImageError,
        ValueError,
    ) as e:
        raise InvalidImageError from e


def create_image_obj(raw: bytes) -> io.BytesIO:
    img = Image.open(io.BytesIO(raw))

    if img.height > MAX_IMAGE_SIZE or img.width > MAX_IMAGE_SIZE:
        img = img.resize((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.ANTIALIAS)

    # remove Alpha channel
    img = img.convert("RGB")

    fp = io.BytesIO()
    img.seek(0)
    img.save(fp, "PNG")

    return fp


def create_random_image_filename(image_url: str, content_type: str | None) -> str:
    """Generate a random filename with correct extension. Raises ValueError
    if invalid"""

    if not image_url:
        raise ValueError("No image_url provided")

    # check path first
    ext: str | None = None

    _, ext = os.path.splitext(urlparse(image_url).path)
    if ext is None:
        raise ValueError("Missing ext:" + image_url)

    if ext not in IMAGE_EXTENSIONS:
        # try to guess extension from content type
        ext = mimetypes.guess_extension(content_type or "")

    if ext is None or ext not in IMAGE_EXTENSIONS:
        raise ValueError("Invalid file extension:" + image_url)
    return uuid.uuid4().hex + ext
