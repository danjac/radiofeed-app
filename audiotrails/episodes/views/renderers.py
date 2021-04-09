from turbo_response import TurboStream


def render_play_next(request, has_more_items):
    return (
        TurboStream("play-next")
        .replace.template("episodes/_play_next.html", {"has_next": has_more_items})
        .render(request=request)
    )


def render_queue_toggle(request, episode, is_queued):
    return (
        TurboStream(episode.dom.queue_toggle)
        .replace.template(
            "episodes/_queue_toggle.html",
            {"episode": episode, "is_queued": is_queued},
        )
        .render(request=request)
    )


def render_remove_from_queue(request, episode, has_more_items):
    if not has_more_items:
        return TurboStream("queue").update.render(
            "You have no more episodes in your Play Queue"
        )
    return TurboStream(episode.dom.queue).remove.render()


def render_favorite_toggle(request, episode, is_favorited):
    return (
        TurboStream(episode.dom.favorite_toggle)
        .replace.template(
            "episodes/_favorite_toggle.html",
            {"episode": episode, "is_favorited": is_favorited},
        )
        .render(request=request)
    )


def render_player_toggle(request, episode, is_playing, is_modal):
    return (
        TurboStream(
            episode.dom.player_modal_toggle if is_modal else episode.dom.player_toggle
        )
        .replace.template(
            "episodes/_player_toggle.html",
            {
                "episode": episode,
                "is_playing": is_playing,
                "is_modal": is_modal,
            },
        )
        .render(request=request)
    )
