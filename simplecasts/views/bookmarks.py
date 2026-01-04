from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST, require_safe

from simplecasts.http.decorators import require_DELETE
from simplecasts.http.request import AuthenticatedHttpRequest
from simplecasts.http.response import HttpResponseConflict
from simplecasts.models import Episode
from simplecasts.services.search import search_queryset
from simplecasts.views.paginator import render_paginated_response


@require_safe
@login_required
def index(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Renders user's bookmarks. User can also search their bookmarks."""
    bookmarks = request.user.bookmarks.select_related("episode", "episode__podcast")

    ordering = request.GET.get("order", "desc")
    order_by = "created" if ordering == "asc" else "-created"

    if request.search:
        bookmarks = search_queryset(
            bookmarks,
            request.search.value,
            "episode__search_vector",
            "episode__podcast__search_vector",
        ).order_by("-rank", order_by)
    else:
        bookmarks = bookmarks.order_by(order_by)

    return render_paginated_response(
        request,
        "bookmarks/index.html",
        bookmarks,
        {
            "ordering": ordering,
        },
    )


@require_POST
@login_required
def add_bookmark(
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse | HttpResponseConflict:
    """Add episode to bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)

    try:
        request.user.bookmarks.create(episode=episode)
    except IntegrityError:
        return HttpResponseConflict()

    messages.success(request, "Added to Bookmarks")

    return _render_bookmark_action(request, episode, is_bookmarked=True)


@require_DELETE
@login_required
def remove_bookmark(
    request: AuthenticatedHttpRequest, episode_id: int
) -> TemplateResponse:
    """Remove episode from bookmarks."""
    episode = get_object_or_404(Episode, pk=episode_id)
    request.user.bookmarks.filter(episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")

    return _render_bookmark_action(request, episode, is_bookmarked=False)


def _render_bookmark_action(
    request: AuthenticatedHttpRequest,
    episode: Episode,
    *,
    is_bookmarked: bool,
) -> TemplateResponse:
    return TemplateResponse(
        request,
        "episodes/detail.html#bookmark_button",
        {
            "episode": episode,
            "is_bookmarked": is_bookmarked,
        },
    )
