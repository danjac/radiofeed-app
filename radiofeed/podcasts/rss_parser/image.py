# Standard Library
import io
import mimetypes
import os
import uuid
from typing import Optional
from urllib.parse import urlparse

# Django
from django.core.files.images import ImageFile

# Third Party Libraries
import requests

# Local
from .headers import get_headers

IMAGE_EXTENSIONS = (".jpg", ".png", ".jpeg")


class InvalidImageURL(Exception):
    ...


def fetch_image_from_url(image_url: str) -> ImageFile:
    """Get an ImageFile object from a URL. """
    try:
        if not image_url:
            raise ValueError("image_url is empty")

        # check head for image size

        resp = requests.head(image_url, headers=get_headers())
        resp.raise_for_status()

        # Max 6MB
        if (content_length := int(resp.headers["Content-Length"]) / 1048576.0) > 6.0:
            raise ValueError(f"{image_url} too large: {content_length}")

        content_type = resp.headers["Content-Type"].split(";")[0]

        filename = get_image_filename(image_url, content_type)

        resp = requests.get(image_url, headers=get_headers(), stream=True)
        resp.raise_for_status()

        return ImageFile(io.BytesIO(resp.content), name=filename)
    except (requests.RequestException, KeyError, ValueError) as e:
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
