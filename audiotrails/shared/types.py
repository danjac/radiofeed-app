from typing import Any, Protocol

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest


class ActionProtocol(Protocol):
    def __call__(
        modeladmin: admin.ModelAdmin, request: HttpRequest, queryset: QuerySet
    ) -> None:
        ...

    short_description: str
    boolean: bool


def admin_action(func: Any) -> ActionProtocol:
    return func
