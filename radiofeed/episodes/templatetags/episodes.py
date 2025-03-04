from django import template
from django.template.context import RequestContext

from radiofeed.cover_image import get_metadata_info
from radiofeed.episodes.models import Episode

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
        "artist": episode.podcast.cleaned_title,
        "artwork": get_metadata_info(context.request, episode.get_cover_url()),
    }
