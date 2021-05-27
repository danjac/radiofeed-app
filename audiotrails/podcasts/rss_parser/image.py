from __future__ import annotations

import io
import logging
import mimetypes
import os
import uuid

from datetime import datetime
from urllib.parse import urlparse

import requests

from django.core.files.images import ImageFile
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError
from requests.structures import CaseInsensitiveDict

from audiotrails.podcasts.rss_parser import http
from audiotrails.podcasts.rss_parser.date_parser import parse_date

MAX_IMAGE_SIZE = 1000
IMAGE_EXTENSIONS = (".jpg", ".png", ".jpeg")

logger = logging.getLogger(__name__)


def fetch_image_from_url(
    image_url: str, last_modified: datetime | None, force_update: bool = False
) -> ImageFile | None:
    """Get an ImageFile object from a URL. Checks if image should be updated, returns
    None if no image or invalid."""
    try:
        if not should_fetch_image(image_url, last_modified, force_update):
            return None

        response = http.get_response(image_url)

        if (content_type := get_content_type(image_url, response.headers)) is None:
            raise ValueError("Content type not provided")

        filename = get_image_filename(image_url, content_type)

        return ImageFile(get_image_file(response.content), name=filename)

    except (
        requests.RequestException,
        DecompressionBombError,
        UnidentifiedImageError,
        ValueError,
    ) as e:
        logging.error(e)
        return None


def get_content_type(image_url: str, headers: CaseInsensitiveDict) -> str:

    try:
        return headers["Content-Type"].split(";")[0]
    except KeyError:
        return mimetypes.guess_type(image_url)[0]


def should_fetch_image(
    image_url: str, last_modified: datetime | None, force_update: bool
) -> bool:
    if not image_url:
        return False

    if force_update or last_modified is None:
        return True

    try:
        headers = http.get_headers(image_url)
    except requests.RequestException:
        return False

    if (
        date := parse_date(headers.get("Last-Modified", None))
    ) and date > last_modified:
        return True

    # a lot of CDNs just return Date as current date/time so not very useful.
    # in this case only update if older than 30 days.

    if (date := parse_date(headers.get("Date", None))) and (
        date - last_modified
    ).days > 30:
        return True

    return False


def get_image_file(raw: bytes) -> io.BytesIO:
    img = Image.open(io.BytesIO(raw))

    if img.height > MAX_IMAGE_SIZE or img.width > MAX_IMAGE_SIZE:
        img = img.resize((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.ANTIALIAS)

    # remove Alpha channel
    img = img.convert("RGB")

    fp = io.BytesIO()
    img.seek(0)
    img.save(fp, "PNG")

    return fp


def get_image_filename(image_url: str, content_type: str) -> str:
    """Generate a random filename with correct extension. Raises ValueError
    if invalid"""

    if not image_url:
        raise ValueError("No image_url provided")

    # check path first
    ext: str | None = None
    _, ext = os.path.splitext(urlparse(image_url).path)
    if ext is None:
        raise ValueError("Missing ext:" + image_url)
    ext = ext.lower()
    if ext not in IMAGE_EXTENSIONS:
        ext = mimetypes.guess_extension(content_type)
    if ext not in IMAGE_EXTENSIONS:
        raise ValueError("Invalid file extension:" + image_url)
    return uuid.uuid4().hex + ext
