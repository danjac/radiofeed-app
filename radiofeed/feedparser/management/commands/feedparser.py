import contextlib

import typer
from django.db.models import Count, F
from django_typer.management import Typer
from rich.progress import track

from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.feedparser.feed_parser import parse_feed
from radiofeed.feedparser.opml_parser import parse_opml
from radiofeed.http_client import get_client
from radiofeed.podcasts.models import Podcast

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
    num_podcasts = podcasts.count()

    for podcast in track(podcasts, description=f"Syncing {num_podcasts} RSS feeds..."):
        with contextlib.suppress(FeedParserError):
            parse_feed(podcast, client)
    typer.secho(f"{num_podcasts} feeds parsed", fg="green")


@app.command()
def import_opml(file: typer.FileBinaryRead) -> None:
    """Import podcasts from an OPML file."""
    Podcast.objects.bulk_create(
        (Podcast(rss=url) for url in parse_opml(file.read())),
        ignore_conflicts=True,
    )
    typer.secho("OPML import completed successfully.", fg="green")
