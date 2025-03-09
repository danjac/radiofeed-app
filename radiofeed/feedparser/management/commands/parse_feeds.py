import djclick as click
from django.db.models import Count, F, QuerySet

from radiofeed.feedparser import feed_parser
from radiofeed.feedparser.exceptions import FeedParserError
from radiofeed.http_client import Client, get_client
from radiofeed.podcasts.models import Podcast
from radiofeed.thread_pool import execute_thread_pool


@click.command()
@click.option(
    "--limit",
    "-l",
    type=int,
    help="Number of feeds to process",
    default=360,
)
def command(*, limit: int) -> None:
    """Parses RSS feeds of all scheduled podcasts."""
    client = get_client()

    execute_thread_pool(
        lambda podcast: _parse_feed(podcast, client),
        _get_scheduled_podcasts(limit),
    )


def _get_scheduled_podcasts(limit: int) -> QuerySet[Podcast]:
    return (
        Podcast.objects.scheduled()
        .alias(subscribers=Count("subscriptions"))
        .filter(active=True)
        .order_by(
            F("subscribers").desc(),
            F("rating").asc(nulls_last=True),
            F("parsed").asc(nulls_first=True),
        )[:limit]
    )


def _parse_feed(podcast: Podcast, client: Client) -> None:
    try:
        feed_parser.parse_feed(podcast, client)
        click.secho(f"{podcast}: Success", fg="green")
    except FeedParserError as e:
        click.secho(f"{podcast}: {e.parser_error.label}", fg="red")
