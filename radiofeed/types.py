from collections.abc import Callable
from typing import TYPE_CHECKING, TypeAlias, TypeVar

from django.http import HttpRequest

if TYPE_CHECKING:  # pragma: no cover
    from django.contrib import admin
    from django.db.models import Model, QuerySet

    from radiofeed.users.models import User

    T_Model = TypeVar("T_Model", bound=Model)
    T_QuerySet: TypeAlias = QuerySet[T_Model]
    T_ModelAdmin: TypeAlias = admin.ModelAdmin
    HttpRequestResponse: TypeAlias = Callable

    class AuthenticatedHttpRequest(HttpRequest):
        """Request with logged-in user."""

        user: User
else:
    T_Model = object
    T_ModelAdmin = object
    T_QuerySet = object

    HttpRequestResponse: TypeAlias = Callable
    AuthenticatedHttpRequest = HttpRequest
