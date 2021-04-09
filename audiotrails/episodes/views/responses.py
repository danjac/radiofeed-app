import json

from django.conf import settings
from turbo_response import TurboStream
from turbo_response.decorators import turbo_stream_response

from audiotrails.pagination import render_paginated_response

from .renderers import (
    render_player_toggle,
    render_queue_toggle,
    render_remove_from_queue,
)
from .services import delete_queue_item


def render_episode_list_response(
    request,
    episodes,
    template_name,
    extra_context=None,
    cached=False,
):

    extra_context = extra_context or {}

    if cached:
        extra_context["cache_timeout"] = settings.DEFAULT_CACHE_TIMEOUT
        pagination_template_name = "episodes/_episodes_cached.html"
    else:
        pagination_template_name = "episodes/_episodes.html"

    return render_paginated_response(
        request,
        episodes,
        template_name,
        pagination_template_name,
        extra_context,
    )


def render_player_response(
    request,
    next_episode=None,
    current_time=0,
    mark_completed=False,
):
    current_episode = request.player.eject(mark_completed=mark_completed)

    if next_episode:
        request.player.start(next_episode, current_time)

    response = render_player_streams(request, current_episode, next_episode)

    response["X-Media-Player"] = json.dumps(
        {"action": "stop"}
        if next_episode is None
        else {
            "action": "start",
            "currentTime": current_time,
            "mediaUrl": next_episode.media_url,
            "metadata": next_episode.get_media_metadata(),
        }
    )

    return response


@turbo_stream_response
def render_player_streams(request, current_episode, next_episode):
    if request.POST.get("is_modal"):
        yield TurboStream("modal").update.render()

    if current_episode:
        for is_modal in (True, False):
            yield render_player_toggle(
                request, current_episode, False, is_modal=is_modal
            )

    if next_episode is None:
        yield TurboStream("player-controls").remove.render()
    else:
        has_more_items = delete_queue_item(request, next_episode)

        yield render_remove_from_queue(request, next_episode, has_more_items)
        yield render_queue_toggle(request, next_episode, False)

        for is_modal in (True, False):
            yield render_player_toggle(request, next_episode, True, is_modal=is_modal)

        yield TurboStream("player").update.template(
            "episodes/_player_controls.html",
            {
                "episode": next_episode,
                "has_next": has_more_items,
            },
        ).render(request=request)
