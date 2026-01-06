from typing import TYPE_CHECKING, TypeGuard

from django.http import HttpRequest as DjangoHttpRequest
from django.template.context import RequestContext as DjangoRequestContext

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django_htmx.middleware import HtmxDetails

    from simplecasts.middleware.player import PlayerDetails
    from simplecasts.middleware.search import SearchDetails
    from simplecasts.models import User


class HttpRequest(DjangoHttpRequest):
    """Extended HttpRequest with user, player, and search details."""

    if TYPE_CHECKING:
        user: User | AnonymousUser
        htmx: HtmxDetails
        player: PlayerDetails
        search: SearchDetails


class AuthenticatedHttpRequest(HttpRequest):
    """HttpRequest guaranteed to have an authenticated user."""

    if TYPE_CHECKING:
        user: User


class RequestContext(DjangoRequestContext):
    """Extended RequestContext with typed request."""

    if TYPE_CHECKING:
        request: HttpRequest


def is_authenticated_request(
    request: HttpRequest,
) -> TypeGuard[AuthenticatedHttpRequest]:
    """Check if the request has an authenticated user."""
    return request.user.is_authenticated
