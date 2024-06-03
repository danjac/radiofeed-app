import djclick as click

from listenwave.feedparser.opml_parser import parse_opml
from listenwave.podcasts.models import Podcast


@click.command(help="Create new podcast feeds from OPML document.")
@click.argument("input", type=click.File("rb"))
@click.option(
    "--promote/--no-promote",
    default=False,
    help="Promote podcasts",
)
def command(input: click.File, *, promote: bool) -> None:
    """Implementation of command."""
    podcasts = Podcast.objects.bulk_create(
        [
            Podcast(
                rss=rss,
                promoted=promote,
            )
            for rss in parse_opml(input.read())
        ],
        ignore_conflicts=True,
    )

    if num_podcasts := len(podcasts):
        click.echo(
            click.style(
                f"{num_podcasts} podcasts imported",
                bold=True,
                fg="green",
            )
        )
    else:
        click.echo(
            click.style(
                "No podcasts found",
                bold=True,
                fg="red",
            )
        )
