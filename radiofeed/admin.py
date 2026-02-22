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
        try:
            return int(cursor.fetchone()[0])
        except IndexError, TypeError, ValueError:
            return 0


class FastCountPaginator(Paginator):
    """Uses pg_class.reltuples for fast unfiltered counts in admin list views."""

    @cached_property
    def count(self) -> int:
        """Return estimated count for unfiltered querysets, else standard count."""
        if (
            isinstance(self.object_list, QuerySet)
            and not self.object_list.query.where.children
        ):
            result = count_reltuples(self.object_list.model._meta.db_table)
            if result > 0:
                return result

        return super().count


class FastCountAdminMixin:
    """Mixin that uses pg_class.reltuples for fast unfiltered counts.

    Sets show_full_result_count=False to prevent Django admin from issuing
    a separate COUNT(*) query for the total results header.
    """

    paginator = FastCountPaginator
    show_full_result_count = False
