from typing import Dict, Optional

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from radiofeed.pagination import render_paginated_response

from ..models import Episode


def get_episode_or_404(episode_id: int) -> Episode:
    return get_object_or_404(Episode, pk=episode_id)


def get_episode_detail_or_404(request: HttpRequest, episode_id: int) -> Episode:
    return get_object_or_404(
        Episode.objects.with_current_time(request.user).select_related("podcast"),
        pk=episode_id,
    )


def render_episode_list_response(
    request: HttpRequest,
    episodes: QuerySet,
    template_name: str,
    extra_context: Optional[Dict] = None,
    cached: bool = False,
) -> HttpResponse:

    extra_context = extra_context or {}

    if cached:
        extra_context["cache_timeout"] = settings.DEFAULT_CACHE_TIMEOUT
        partial_template_name = "episodes/list/_episode_list_cached.html"
    else:
        partial_template_name = "episodes/list/_episode_list.html"

    return render_paginated_response(
        request, episodes, template_name, partial_template_name, extra_context
    )
