import io
import mimetypes
import os
import uuid

from typing import Optional
from urllib.parse import urlparse

import requests

from django.core.files.images import ImageFile
from PIL import Image, UnidentifiedImageError

from .headers import get_headers

MAX_IMAGE_SIZE = 1000
IMAGE_EXTENSIONS = (".jpg", ".png", ".jpeg")


class InvalidImageURL(Exception):
    ...


def fetch_image_from_url(image_url: str) -> ImageFile:
    """Get an ImageFile object from a URL. """
    try:
        if not image_url:
            raise ValueError("image_url is empty")

        resp = requests.get(image_url, headers=get_headers(), stream=True)
        resp.raise_for_status()

        content_type = resp.headers["Content-Type"].split(";")[0]

        img = Image.open(io.BytesIO(resp.content))

        if img.height > MAX_IMAGE_SIZE or img.width > MAX_IMAGE_SIZE:
            img = img.resize((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.ANTIALIAS)

        # remove Alpha channel
        img = img.convert("RGB")

        filename = get_image_filename(image_url, content_type)

        fp = io.BytesIO()
        img.seek(0)
        img.save(fp, "PNG")

        return ImageFile(fp, name=filename)

    except (
        requests.RequestException,
        UnidentifiedImageError,
        KeyError,
        ValueError,
    ) as e:
        raise InvalidImageURL from e


def get_image_filename(image_url: str, content_type: str) -> str:
    """Generate a random filename with correct extension. Raises ValueError
    if invalid"""

    if not image_url:
        raise ValueError("No image_url provided")

    # check path first
    ext: Optional[str] = None
    _, ext = os.path.splitext(urlparse(image_url).path)
    ext = ext.lower()
    if ext not in IMAGE_EXTENSIONS:
        ext = mimetypes.guess_extension(content_type)
    if ext not in IMAGE_EXTENSIONS:
        raise ValueError("Invalid file extension:" + image_url)
    return uuid.uuid4().hex + ext
