from typing import Dict, Optional

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from radiofeed.pagination import render_paginated_response

from ..models import Podcast


def get_podcast_or_404(podcast_id: int) -> Podcast:
    return get_object_or_404(Podcast, pk=podcast_id)


def render_podcast_list_response(
    request: HttpRequest,
    podcasts: QuerySet,
    template_name: str,
    extra_context: Optional[Dict] = None,
    cached: bool = False,
) -> HttpResponse:

    extra_context = extra_context or {}

    if cached:
        extra_context["cache_timeout"] = settings.DEFAULT_CACHE_TIMEOUT
        partial_template_name = "podcasts/list/_podcast_list_cached.html"
    else:
        partial_template_name = "podcasts/list/_podcast_list.html"

    return render_paginated_response(
        request, podcasts, template_name, partial_template_name, extra_context
    )
