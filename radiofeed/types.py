from typing import TYPE_CHECKING, TypeAlias, TypeVar

if TYPE_CHECKING:  # pragma: no cover
    from django.contrib import admin
    from django.db.models import Model, QuerySet

    T_Model = TypeVar("T_Model", bound=Model)
    T_QuerySet: TypeAlias = QuerySet[T_Model]
    T_ModelAdmin: TypeAlias = admin.ModelAdmin

else:
    T_Model = object
    T_ModelAdmin = object
    T_QuerySet = object
