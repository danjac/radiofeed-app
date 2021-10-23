from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, Type, TypeVar

from mypy.nodes import NameExpr
from mypy.options import Options
from mypy.plugin import DynamicClassDefContext, Plugin

T = TypeVar("T")
DynamicClassDef = DynamicClassDefContext


def with_typehint(baseclass: Type[T], runtime_class: Type[T] | None = None) -> Type[T]:
    if TYPE_CHECKING:
        return baseclass

    return runtime_class or object  # type: ignore


class DynamicClassPlugin(Plugin):
    def __init__(self, options: Options):
        super().__init__(options)

        self.named_placeholders: Dict[str, str] = {}

    def get_dynamic_class_hook(self, fullname: str) -> Callable | None:
        if fullname == "jcasts.shared.typehints.with_typehint":

            def hook(ctx: DynamicClassDefContext):
                klass = ctx.call.args[0]
                assert isinstance(klass, NameExpr)  # nosec

                type_name = klass.fullname
                assert type_name is not None  # nosec

                qualified = self.lookup_fully_qualified(type_name)
                assert qualified is not None  # nosec

                ctx.api.add_symbol_table_node(ctx.name, qualified)

            return hook

        return None


def plugin(_version: str):
    return DynamicClassPlugin
