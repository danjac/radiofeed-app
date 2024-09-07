import djclick as click
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from radiofeed.feedparser import opml_parser
from radiofeed.podcasts.models import Podcast


@click.group(invoke_without_command=True)
def opml():
    """OPML commands."""


@opml.command(name="parse")
@click.argument("file", type=click.File("rb"))
@click.option("--promote/--no-promote", default=False, help="Promote imported podcasts")
def parse(file: click.File, *, promote: bool) -> None:
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


@opml.command(name="export")
@click.argument("file", type=click.File("w"))
@click.option(
    "--promoted/--not-promoted",
    default=False,
    help="Export only promoted podcasts",
)
def export(file, *, promoted: bool):
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
