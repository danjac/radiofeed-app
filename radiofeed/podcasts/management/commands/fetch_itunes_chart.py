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
@click.option(
    "--clear",
    type=bool,
    help="Clear the database before fetching",
    is_flag=True,
    default=False,
)
def command(**options):
    """Crawl iTunes Top Chart."""
    for podcast in itunes.fetch_chart(get_client(), **options):
        click.secho(str(podcast), fg="green")
