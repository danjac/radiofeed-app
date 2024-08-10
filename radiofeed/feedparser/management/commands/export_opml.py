import djclick as click
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from radiofeed.podcasts.models import Podcast


@click.command(help="Generate OPML document from all public feeds")
@click.argument("output", type=click.File("w"))
@click.option(
    "--promoted/--no-promoted",
    default=False,
    help="Export only promoted podcasts",
)
def command(output: click.File, *, promoted: bool) -> None:
    """Implementation of command."""
    podcasts = Podcast.objects.filter(
        private=False,
        pub_date__isnull=False,
    ).order_by("title")

    if promoted:
        podcasts = podcasts.filter(promoted=True)
    output.write(
        render_to_string(
            "feedparser/podcasts.opml",
            {
                "podcasts": podcasts,
                "site": Site.objects.get_current(),
            },
        )
    )
    click.echo(
        click.style(
            f"{podcasts.count()} podcasts exported",
            bold=True,
            fg="green",
        )
    )
