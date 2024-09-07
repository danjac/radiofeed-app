import djclick as click

from radiofeed.feedparser.opml_parser import parse_opml
from radiofeed.podcasts.models import Podcast


@click.command()
@click.argument("file", type=click.File("rb"))
@click.option("--promote/--no-promote", default=False, help="Promote imported podcasts")
def command(file: click.File, *, promote: bool) -> None:
    """Create new podcast feeds from OPML document"""

    podcasts = Podcast.objects.bulk_create(
        [
            Podcast(
                rss=rss,
                promoted=promote,
            )
            for rss in parse_opml(file.read())
        ],
        ignore_conflicts=True,
    )

    if num_podcasts := len(podcasts):
        click.echo(click.style(f"{num_podcasts} podcasts imported", fg="green"))
    else:
        click.echo(click.style("No podcasts found", fg="red"))
