from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django_htmx.middleware import HtmxDetails

from radiofeed.common.middleware import Search
from radiofeed.episodes.middleware import Player
from radiofeed.users.models import User


class Request(HttpRequest):
    user: User | AnonymousUser
    htmx: HtmxDetails
    search: Search
    player: Player


class AuthenticatedRequest(Request):
    user: User
