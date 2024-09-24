import http
from typing import TYPE_CHECKING

from django.http import HttpRequest as DjangoHttpRequest
from django.http import HttpResponse
from django.template.context import RequestContext as DjangoRequestContext
from django.views.decorators.http import require_http_methods

require_form_methods = require_http_methods(["GET", "HEAD", "POST"])

require_DELETE = require_http_methods(["DELETE"])  # noqa: N816

if TYPE_CHECKING:  # pragma: no cover
    from django_htmx.middleware import HtmxDetails

    from radiofeed.episodes.middleware import PlayerDetails
    from radiofeed.middleware import SearchDetails
    from radiofeed.users.models import User

    class HttpRequest(DjangoHttpRequest):
        """HttpRequest annotated with middleware-provided properties."""

        htmx: HtmxDetails
        player: PlayerDetails
        search: SearchDetails

    class UserRequest(HttpRequest):
        """Ensures always using logged-in user."""

        user: User

    class RequestContext(DjangoRequestContext):
        """Annotated RequestContext"""

        request: HttpRequest

else:
    UserRequest = HttpRequest = DjangoHttpRequest
    RequestContext = DjangoRequestContext


class HttpResponseNoContent(HttpResponse):
    """204 No Content response."""

    status_code = http.HTTPStatus.NO_CONTENT


class HttpResponseUnauthorized(HttpResponse):
    """401 Unauthorized response."""

    status_code = http.HTTPStatus.UNAUTHORIZED


class HttpResponseConflict(HttpResponse):
    """409 Conflict response."""

    status_code = http.HTTPStatus.CONFLICT
