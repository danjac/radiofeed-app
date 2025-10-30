from typing import Annotated

import typer
from django.db.models import Case, Count, IntegerField, QuerySet, When
from django_typer.management import TyperCommand

from radiofeed.feedparser.feed_parser import parse_feed
from radiofeed.http_client import get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool


class Command(TyperCommand):
    """Parse feeds for all active podcasts."""

    def handle(
        self,
        *,
        limit: Annotated[
            int,
            typer.Option(help="Number of podcasts to parse"),
        ] = 360,
    ) -> None:
        """Parse feeds for all active podcasts."""

        client = get_client()

        def _parse_feed(podcast: Podcast) -> Podcast.ParserResult:
            result = parse_feed(podcast, client)
            color = (
                typer.colors.GREEN
                if result is Podcast.ParserResult.SUCCESS
                else typer.colors.RED
            )
            self.secho(f"{podcast}: {result.label}", fg=color)
            return result

        execute_thread_pool(_parse_feed, self._get_scheduled_podcasts(limit))

    def _get_scheduled_podcasts(self, limit: int) -> QuerySet[Podcast]:
        """Get scheduled podcasts with a limit."""
        return (
            Podcast.objects.scheduled()
            .annotate(
                subscribers=Count("subscriptions"),
                is_new=Case(
                    When(parsed__isnull=True, then=1),
                    default=0,
                    output_field=IntegerField(),
                ),
            )
            .filter(active=True)
            .order_by(
                "-is_new",
                "-subscribers",
                "-promoted",
                "parsed",
                "updated",
            )[:limit]
        )
