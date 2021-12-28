from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods

from jcasts.episodes.models import Bookmark, Episode
from jcasts.episodes.views import get_episode_or_404
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.paginate import paginate
from jcasts.shared.response import HttpResponseConflict


@require_http_methods(["GET"])
@login_required
def index(request: HttpRequest) -> HttpResponse:
    bookmarks = Bookmark.objects.filter(user=request.user).select_related(
        "episode", "episode__podcast"
    )
    if request.search:
        bookmarks = bookmarks.search(request.search.value).order_by("-rank", "-created")
    else:
        bookmarks = bookmarks.order_by("-created")

    return TemplateResponse(
        request,
        "episodes/bookmarks.html",
        {
            "page_obj": paginate(request, bookmarks),
        },
    )


@require_http_methods(["POST"])
@ajax_login_required
def add_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id, with_podcast=True)

    try:
        Bookmark.objects.create(episode=episode, user=request.user)
        messages.success(request, "Added to Bookmarks")
        return render_bookmark_toggle(request, episode, is_bookmarked=True)
    except IntegrityError:
        return HttpResponseConflict()


@require_http_methods(["DELETE"])
@ajax_login_required
def remove_bookmark(request: HttpRequest, episode_id: int) -> HttpResponse:
    episode = get_episode_or_404(request, episode_id)

    Bookmark.objects.filter(user=request.user, episode=episode).delete()

    messages.info(request, "Removed from Bookmarks")
    return render_bookmark_toggle(request, episode, is_bookmarked=False)


def render_bookmark_toggle(
    request: HttpRequest, episode: Episode, is_bookmarked: bool
) -> HttpResponse:
    return TemplateResponse(
        request,
        "episodes/_bookmark_toggle.html",
        {
            "episode": episode,
            "is_bookmarked": is_bookmarked,
        },
    )
