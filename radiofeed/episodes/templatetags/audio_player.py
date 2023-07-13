from django import template
from django.conf import settings
from django.http import HttpRequest
from django.template.context import RequestContext
from django.templatetags.static import static

from radiofeed.episodes.models import Episode
from radiofeed.template import COVER_IMAGE_SIZES, cover_image_url

register = template.Library()


@register.simple_tag(takes_context=True)
def get_media_metadata(context: RequestContext, episode: Episode) -> dict:
    """Returns media session metadata for integration with client device.

    For more details:

        https://developers.google.com/web/updates/2017/02/media-session
    """

    return {
        "title": episode.cleaned_title,
        "album": episode.podcast.cleaned_title,
        "artist": episode.podcast.owner,
        "artwork": [
            {
                "src": _cover_image_url(
                    context.request,
                    episode.podcast.cover_url,
                    size,
                ),
                "sizes": f"{size}x{size}",
                "type": "image/webp",
            }
            for size in COVER_IMAGE_SIZES
        ],
    }


@register.inclusion_tag("episodes/_audio_player.html", takes_context=True)
def audio_player(context: RequestContext) -> dict:
    """Returns details of current episode in player."""
    if (episode_id := context.request.player.get()) and (
        audio_log := context.request.user.audio_logs.filter(episode__pk=episode_id)
        .select_related("episode", "episode__podcast")
        .first()
    ):
        return {
            "audio_log": audio_log,
            "is_playing": True,
            "request": context.request,
        }

    return {}


def _cover_image_url(request: HttpRequest, cover_url: str | None, size: int) -> str:
    if cover_url:
        return request.build_absolute_uri(cover_image_url(cover_url, size=size))

    placeholder_url = static(f"img/placeholder-{size}.webp")

    return (
        placeholder_url
        if settings.STATIC_URL.startswith("http")
        else request.build_absolute_uri(placeholder_url)
    )
