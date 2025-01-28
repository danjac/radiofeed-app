from typing import TypedDict

from django import template

from radiofeed.podcasts.models import Podcast

register = template.Library()


class Season(TypedDict):
    """Season dictionary."""

    label: str
    url: str


@register.simple_tag
def get_podcast_seasons(podcast: Podcast, current_season: int | None = None) -> dict:
    """Return a list of seasons."""

    current = None
    items = []

    if (
        seasons := podcast.episodes.filter(season__isnull=False)
        .values_list("season", flat=True)
        .order_by("season")
        .distinct()
    ):
        episodes_url = podcast.get_episodes_url()
        items = {
            season: Season(
                label=f"Season {season}",
                url=f"{episodes_url}?season={season}",
            )
            for season in seasons
        }
        if current_season:
            current = items.pop(current_season, None)
        items = [Season(label="All Seasons", url=episodes_url), *items.values()]

    return {
        "current": current,
        "items": items,
    }
