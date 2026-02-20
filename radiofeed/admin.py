from django.core.paginator import Paginator
from django.db import connection
from django.db.models import QuerySet
from django.utils.functional import cached_property


def count_reltuples(table_name: str) -> int:
    """Get estimated row count from pg_class reltuples."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT reltuples::bigint FROM pg_class WHERE oid = %s::regclass",
            [table_name],
        )
        result = cursor.fetchone()
        return int(result[0]) if result else 0


class FastCountPaginator(Paginator):
    """Uses pg_class.reltuples for fast unfiltered counts in admin list views."""

    @cached_property
    def count(self) -> int:  # type: ignore[override]
        """Return estimated count for unfiltered querysets, else standard count."""
        if not isinstance(self.object_list, QuerySet):
            return len(self.object_list)

        if not self.object_list.query.where.children:
            result = count_reltuples(self.object_list.model._meta.db_table)
            if result > 0:
                return result

        return self.object_list.count()


class FastCountMixin:
    """Mixin that uses pg_class.reltuples for fast unfiltered counts.

    Sets show_full_result_count=False to prevent Django admin from issuing
    a separate COUNT(*) query for the total results header.
    """

    paginator = FastCountPaginator
    show_full_result_count = False
