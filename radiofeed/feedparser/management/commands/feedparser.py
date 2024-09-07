import contextlib
from concurrent.futures import wait

import djclick as click
from django.contrib.sites.models import Site
from django.db.models import Count, F, QuerySet
from django.template.loader import render_to_string

from radiofeed.feedparser import feed_parser, opml_parser, scheduler
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import Client, get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import DatabaseSafeThreadPoolExecutor


@click.group(invoke_without_command=True)
def cli():
    """Feedparser commands."""


@cli.command(name="parse_feeds")
@click.option("--limit", type=int, default=360, help="Number of feeds to process")
def parse_feeds(limit: int) -> None:
    "Parses RSS feeds of all scheduled podcasts"

    client = get_client()

    with DatabaseSafeThreadPoolExecutor() as executor:
        wait(
            executor.db_safe_map(
                lambda podcast: _parse_feed(podcast, client),
                _get_scheduled_podcasts(limit),
            )
        )


@cli.command(name="parse_opml")
@click.argument("file", type=click.File("rb"))
@click.option("--promote/--no-promote", default=False, help="Promote imported podcasts")
def parse_opml(file: click.File, *, promote: bool) -> None:
    """Create new podcast feeds from OPML document"""

    podcasts = Podcast.objects.bulk_create(
        [
            Podcast(
                rss=rss,
                promoted=promote,
            )
            for rss in opml_parser.parse_opml(file.read())
        ],
        ignore_conflicts=True,
    )

    if num_podcasts := len(podcasts):
        click.echo(click.style(f"{num_podcasts} podcasts imported", fg="green"))
    else:
        click.echo(click.style("No podcasts found", fg="red"))


@cli.command(name="export_opml")
@click.argument("file", type=click.File("w"))
@click.option(
    "--promoted/--not-promoted",
    default=False,
    help="Export only promoted podcasts",
)
def export_opml(file, *, promoted: bool):
    "Generate OPML document from all public feeds"
    podcasts = Podcast.objects.filter(
        private=False,
        pub_date__isnull=False,
    ).order_by("title")

    if promoted:
        podcasts = podcasts.filter(promoted=True)

    file.write(
        render_to_string(
            "feedparser/podcasts.opml",
            {
                "podcasts": podcasts,
                "site": Site.objects.get_current(),
            },
        )
    )


def _get_scheduled_podcasts(limit: int) -> QuerySet[Podcast]:
    return (
        scheduler.get_scheduled_podcasts()
        .alias(subscribers=Count("subscriptions"))
        .filter(active=True)
        .order_by(
            F("subscribers").desc(),
            F("promoted").desc(),
            F("parsed").asc(nulls_first=True),
        )[:limit]
    )


def _parse_feed(podcast: Podcast, client: Client) -> None:
    with contextlib.suppress(FeedParserError):
        feed_parser.parse_feed(podcast, client)
