from typing import Dict, Optional, Union

from django import template
from django.template.context import RequestContext
from django.urls import reverse

from radiofeed.podcasts.models import CoverImage

from .. import utils
from ..models import Episode
from ..player import PlayerInfo

register = template.Library()


@register.simple_tag(takes_context=True)
def get_player(context: RequestContext) -> PlayerInfo:
    return context["request"].player.as_dict()


@register.filter
def format_duration(total_seconds: Optional[int]) -> Union[str, int]:
    try:
        return utils.format_duration(int(total_seconds or 0))
    except ValueError:
        return 0


@register.inclusion_tag("episodes/_episode.html", takes_context=True)
def episode(
    context: RequestContext,
    episode: Episode,
    dom_id: str = "",
    podcast_url: str = "",
    preview_url: str = "",
    remove_url: str = "",
    cover_image: Optional[CoverImage] = None,
    **attrs,
) -> Dict:
    return {
        "episode": episode,
        "podcast": episode.podcast,
        "dom_id": dom_id or episode.dom.list_item,
        "duration": episode.get_duration_in_seconds(),
        "episode_url": episode.get_absolute_url(),
        "podcast_url": podcast_url or episode.podcast.get_absolute_url(),
        "preview_url": preview_url
        or reverse("episodes:episode_preview", args=[episode.id]),
        "remove_url": remove_url,
        "cover_image": cover_image,
        "is_playing": context["request"].player.is_playing(episode),
        "attrs": attrs,
    }
