from typing import TYPE_CHECKING

from django.template.context import RequestContext as DjangoRequestContext

if TYPE_CHECKING:
<<<<<<< HEAD
    from listenwave.request import Request
=======
    from listenwave.request import HttpRequest
>>>>>>> 1cf2a6a26 (refactor: typing fixes)


class RequestContext(DjangoRequestContext):
    """Extended RequestContext with typed request."""

    if TYPE_CHECKING:
<<<<<<< HEAD
        request: Request
=======
        request: HttpRequest
>>>>>>> 1cf2a6a26 (refactor: typing fixes)
