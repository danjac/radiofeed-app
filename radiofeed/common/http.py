from __future__ import annotations

import http

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest as _HttpRequest
from django.http import HttpResponse
from django_htmx.middleware import HtmxDetails

from radiofeed.common.middleware import Search
from radiofeed.episodes.middleware import Player
from radiofeed.users.models import User


class HttpRequest(_HttpRequest):
    """Typed request class."""

    htmx: HtmxDetails
    player: Player
    search: Search
    user: User | AnonymousUser


class HttpResponseConflict(HttpResponse):
    """HTTP CONFLICT response."""

    status_code: int = http.HTTPStatus.CONFLICT


class HttpResponseNoContent(HttpResponse):
    """HTTP NO CONTENT response."""

    status_code: int = http.HTTPStatus.NO_CONTENT


class HttpResponseUnauthorized(HttpResponse):
    """HTTP UNAUTHORIZED response."""

    status_code: int = http.HTTPStatus.UNAUTHORIZED
