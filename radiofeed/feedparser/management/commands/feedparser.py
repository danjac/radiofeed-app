import typer
from django.db.models import Count, F
from django_typer.management import Typer

from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.feedparser.feed_parser import parse_feed
from radiofeed.feedparser.opml_parser import parse_opml
from radiofeed.http_client import get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool

app = Typer(name="feedparser")


@app.command()
def parse_feeds(limit: int = 360) -> None:
    """Parse feeds for all active podcasts."""

    podcasts = (
        Podcast.objects.scheduled()
        .alias(subscribers=Count("subscriptions"))
        .filter(active=True)
        .order_by(
            F("subscribers").desc(),
            F("itunes_ranking").asc(nulls_last=True),
            F("parsed").asc(nulls_first=True),
        )[:limit]
    )

    client = get_client()

    def _parse_feed(podcast: Podcast) -> None:
        """Parse a single feed."""
        try:
            parse_feed(podcast, client)
            typer.secho(f"{podcast}: Success", fg="green")
        except FeedParserError as exc:
            typer.secho(f"{podcast}: {exc.parser_error.label}", fg="red")

    execute_thread_pool(_parse_feed, podcasts)


@app.command()
def import_opml(file: typer.FileBinaryRead) -> None:
    """Import podcasts from an OPML file."""
    Podcast.objects.bulk_create(
        (Podcast(rss=url) for url in parse_opml(file.read())),
        ignore_conflicts=True,
    )
    typer.secho("OPML import completed successfully.", fg="green")
