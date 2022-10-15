from __future__ import annotations

from typing import TYPE_CHECKING, Callable, TypeAlias, TypeVar

from django.contrib import admin
from django.db.models import Model, QuerySet
from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:  # pragma: no cover
    T_Model = TypeVar("T_Model", bound=Model)
    T_QuerySet: TypeAlias = QuerySet[T_Model]
    T_ModelAdmin: TypeAlias = admin.ModelAdmin
else:
    T_Model = object
    T_ModelAdmin = object
    T_QuerySet = object


GetResponse = Callable[[HttpRequest], HttpResponse]
