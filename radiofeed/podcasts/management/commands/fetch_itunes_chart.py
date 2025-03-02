import djclick as click

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes


@click.command()
@click.option(
    "--location",
    type=str,
    help="iTunes location",
    default="gb",
)
@click.option(
    "--limit",
    type=int,
    help="Limit the number of podcasts to fetch",
    default=50,
)
def command(*, location: str, limit: int):
    """Crawl iTunes Top Chart."""
    for podcast in itunes.fetch_chart(
        get_client(),
        location=location,
        limit=limit,
    ):
        click.secho(str(podcast), fg="green")
