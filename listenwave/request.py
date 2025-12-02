from typing import TYPE_CHECKING, TypeGuard

from django.http import HttpRequest

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django_htmx.middleware import HtmxDetails

    from listenwave.episodes.middleware import PlayerDetails
    from listenwave.middleware import SearchDetails
    from listenwave.users.models import User


class Request(HttpRequest):
    """Extended HttpRequest with user, player, and search details."""

    if TYPE_CHECKING:
        user: User | AnonymousUser
        htmx: HtmxDetails
        player: PlayerDetails
        search: SearchDetails


class AuthenticatedRequest(Request):
    """HttpRequest guaranteed to have an authenticated user."""

    if TYPE_CHECKING:
        user: User


def is_authenticated_request(request: Request) -> TypeGuard[AuthenticatedRequest]:
    """Check if the request has an authenticated user."""
    return request.user.is_authenticated
