from typing import TYPE_CHECKING

from django.template.context import RequestContext as DjangoRequestContext

if TYPE_CHECKING:
    from listenwave.request import HttpRequest


class RequestContext(DjangoRequestContext):
    """Extended RequestContext with typed request."""

    if TYPE_CHECKING:
        request: HttpRequest
