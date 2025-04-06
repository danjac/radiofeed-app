from django import template
from django.template.context import RequestContext

from radiofeed import cover_image
from radiofeed.episodes.models import Episode

register = template.Library()


@register.simple_tag(takes_context=True)
def get_media_metadata(context: RequestContext, episode: Episode) -> dict:
    """Returns media session metadata for integration with client device.

    For more details:

        https://developers.google.com/web/updates/2017/02/media-session

    Use with `json_script` template tag to render the JSON in a script tag.
    """

    return {
        "title": episode.cleaned_title,
        "album": episode.podcast.cleaned_title,
        "artist": episode.podcast.cleaned_title,
        "artwork": cover_image.get_metadata_info(
            context.request, episode.get_cover_url()
        ),
    }
