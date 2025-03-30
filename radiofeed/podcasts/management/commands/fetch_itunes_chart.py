import djclick as click

from radiofeed.http_client import get_client
from radiofeed.podcasts import itunes


@click.command()
@click.argument("country")
@click.option(
    "--limit",
    "-l",
    type=int,
    help="Limit the number of podcasts to fetch",
    default=30,
)
def command(**options):
    """Crawl iTunes Top Chart."""
    for podcast in itunes.fetch_chart(get_client(), **options):
        click.secho(str(podcast), fg="green")
