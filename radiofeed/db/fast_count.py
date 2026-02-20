from typing import TYPE_CHECKING, TypeAlias

from django.db import connection

if TYPE_CHECKING:
    from django.db.models import QuerySet

    Base: TypeAlias = QuerySet

else:
    Base = object


def count_reltuples(table_name: str) -> int:
    """Get estimated row count from pg_class reltuples."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT reltuples::bigint FROM pg_class WHERE oid = %s::regclass",
            [table_name],
        )
        result = cursor.fetchone()
        return int(result[0]) if result else 0


class FastCount(Base):
    """Uses pg_class.reltuples for fast unfiltered counts."""

    def count(self) -> int:
        """Return estimated count if no filters, else standard count."""
        if self.query.where.children:
            return super().count()  # type: ignore[union-attr]

        result = count_reltuples(self.model._meta.db_table)
        if result > 0:
            return result
        return super().count()  # type: ignore[union-attr]
