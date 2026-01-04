from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_safe

from simplecasts.http.request import AuthenticatedHttpRequest
from simplecasts.models import Episode, Podcast


@require_safe
@login_required
def index(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """List latest episodes from subscriptions."""

    latest_episodes = (
        Podcast.objects.subscribed(request.user)
        .annotate(
            latest_episode=Subquery(
                Episode.objects.filter(podcast_id=OuterRef("pk"))
                .order_by("-pub_date", "-pk")
                .values("pk")[:1]
            )
        )
        .filter(latest_episode__isnull=False)
        .order_by("-pub_date")
        .values_list("latest_episode", flat=True)[: settings.DEFAULT_PAGE_SIZE]
    )

    episodes = (
        Episode.objects.filter(pk__in=latest_episodes)
        .select_related("podcast")
        .order_by("-pub_date", "-pk")
    )

    return TemplateResponse(
        request,
        "episodes/index.html",
        {
            "episodes": episodes,
        },
    )


@require_safe
@login_required
def detail(
    request: AuthenticatedHttpRequest,
    episode_id: int,
    slug: str | None = None,
) -> TemplateResponse:
    """Renders episode detail."""
    episode = get_object_or_404(
        Episode.objects.select_related("podcast"),
        pk=episode_id,
    )

    audio_log = request.user.audio_logs.filter(episode=episode).first()

    is_bookmarked = request.user.bookmarks.filter(episode=episode).exists()
    is_playing = request.player.has(episode.pk)

    return TemplateResponse(
        request,
        "episodes/detail.html",
        {
            "episode": episode,
            "audio_log": audio_log,
            "is_bookmarked": is_bookmarked,
            "is_playing": is_playing,
        },
    )
