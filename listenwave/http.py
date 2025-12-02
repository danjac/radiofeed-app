import http
from typing import TYPE_CHECKING

from django.http import HttpRequest as DjangoHttpRequest
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser
    from django_htmx.middleware import HtmxDetails

    from listenwave.episodes.middleware import PlayerDetails
    from listenwave.middleware import SearchDetails
    from listenwave.users.models import User

    class HttpRequest(DjangoHttpRequest):
        """Extended HttpRequest with user, player, and search details."""

        user: User | AnonymousUser
        htmx: HtmxDetails
        player: PlayerDetails
        search: SearchDetails

    class AuthenticatedHttpRequest(HttpRequest):
        """HttpRequest guaranteed to have an authenticated user."""

        user: User


else:
    HttpRequest = DjangoHttpRequest
    AuthenticatedHttpRequest = DjangoHttpRequest

require_form_methods = require_http_methods(["GET", "HEAD", "POST"])

require_DELETE = require_http_methods(["DELETE"])  # noqa: N816


class TextResponse(HttpResponse):
    """Plain text response."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize a plain text HTTP response."""
        kwargs.setdefault("content_type", "text/plain")
        super().__init__(*args, **kwargs)


class HttpResponseNoContent(HttpResponse):
    """204 No Content response."""

    status_code = http.HTTPStatus.NO_CONTENT


class HttpResponseConflict(HttpResponse):
    """409 Conflict response."""

    status_code = http.HTTPStatus.CONFLICT
