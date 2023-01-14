from __future__ import annotations

import urllib.parse

from django.conf import settings
from django.contrib.sites.models import Site
from django.http import HttpRequest


def build_absolute_uri(url: str = "", request: HttpRequest | None = None) -> str:
    """Build absolute URI from request, falling back to current Site if unavailable."""
    url = url or "/"

    if request is not None:
        return request.build_absolute_uri(url)

    return urllib.parse.urljoin(
        settings.HTTP_PROTOCOL + "://" + Site.objects.get_current().domain, url
    )
