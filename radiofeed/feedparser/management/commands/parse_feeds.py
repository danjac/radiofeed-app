import djclick as click

from radiofeed.feedparser import jobs


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
    jobs.parse_feeds(limit=limit)
