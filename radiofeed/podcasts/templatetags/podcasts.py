from django import template

from radiofeed.podcasts.models import Podcast
from radiofeed.templatetags import DropdownContext

register = template.Library()


@register.simple_tag
def get_podcast_seasons(
    podcast: Podcast, selected: int | None = None
) -> DropdownContext:
    """Return a list of seasons."""

    dropdown = DropdownContext(selected=selected)

    if (
        seasons := podcast.episodes.filter(season__isnull=False)
        .values_list("season", flat=True)
        .order_by("season")
        .distinct()
    ):
        episodes_url = podcast.get_episodes_url()
        dropdown.add(
            label="All Seasons",
            url=episodes_url,
        )
        for season in seasons:
            dropdown.add(
                key=season,
                label=f"Season {season}",
                url=f"{episodes_url}?season={season}",
            )

    return dropdown
