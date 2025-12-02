from typing import TYPE_CHECKING

from django.template.context import RequestContext as DjangoRequestContext

if TYPE_CHECKING:
    from listenwave.http import AuthenticatedHttpRequest, HttpRequest

    class RequestContext(DjangoRequestContext):
        """Extended RequestContext with typed request."""

        request: HttpRequest

    class AuthenticatedRequestContext(RequestContext):
        """RequestContext with an authenticated user."""

        request: AuthenticatedHttpRequest

else:
    RequestContext = DjangoRequestContext
    AuthenticatedRequestContext = DjangoRequestContext
