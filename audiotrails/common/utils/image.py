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

from audiotrails.common.utils.http import get_response

MAX_IMAGE_SIZE = 1000
IMAGE_EXTENSIONS = (".jpg", ".png", ".jpeg")


class InvalidImageError(ValueError):
    ...


def fetch_image_file_from_url(url: str) -> ImageFile | None:

    try:
        response = get_response(url)
        return ImageFile(
            create_image_obj(response.content),
            name=create_random_image_filename(url, get_content_type(url, response)),
        )
    except (
        requests.RequestException,
        DecompressionBombError,
        UnidentifiedImageError,
        ValueError,
    ) as e:
        raise InvalidImageError from e


def get_content_type(url: str, response: requests.Response) -> str:
    try:
        return response.headers["Content-Type"].split(";")[0]
    except KeyError:
        return mimetypes.guess_type(url)[0] or ""


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


def create_random_image_filename(url: str, content_type: str) -> str:
    """Generate a random filename with correct extension. Raises ValueError
    if invalid"""

    if not url:
        raise ValueError("No url provided")

    # check path first
    ext: str | None = None

    _, ext = os.path.splitext(urlparse(url).path)

    # try to guess extension from content type
    if ext not in IMAGE_EXTENSIONS:
        ext = mimetypes.guess_extension(content_type)

    if ext is None:
        raise ValueError("Missing ext:" + url)

    if ext not in IMAGE_EXTENSIONS:
        raise ValueError("Invalid file extension:" + url)

    return uuid.uuid4().hex + ext
