from typing import Any, Protocol, Union

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import AnonymousUser
from django.db.models import QuerySet
from django.http import HttpRequest

AnyUser = Union[settings.AUTH_USER_MODEL, AnonymousUser]


class ActionProtocol(Protocol):
    def __call__(
        modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet
    ) -> str:
        ...

    short_description: str
    boolean: bool


def admin_action(func: Any) -> ActionProtocol:
    return func
