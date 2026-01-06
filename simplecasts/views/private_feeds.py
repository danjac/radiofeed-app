from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_safe

from simplecasts.forms import PodcastForm
from simplecasts.http.decorators import require_DELETE, require_form_methods
from simplecasts.http.request import AuthenticatedHttpRequest
from simplecasts.http.response import RenderOrRedirectResponse
from simplecasts.models import Podcast
from simplecasts.models.search import search_queryset
from simplecasts.views.paginator import render_paginated_response
from simplecasts.views.partials import render_partial_response


@require_safe
@login_required
def index(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Lists user's private feeds."""
    podcasts = Podcast.objects.published().filter(private=True).subscribed(request.user)

    if request.search:
        podcasts = search_queryset(
            podcasts,
            request.search.value,
            "search_vector",
        ).order_by("-rank", "-pub_date")
    else:
        podcasts = podcasts.order_by("-pub_date")

    return render_paginated_response(request, "private_feeds/index.html", podcasts)


@require_form_methods
@login_required
def add_private_feed(request: AuthenticatedHttpRequest) -> RenderOrRedirectResponse:
    """Add new private feed to collection."""
    if request.method == "POST":
        form = PodcastForm(request.POST)
        if form.is_valid():
            podcast = form.save(commit=False)
            podcast.private = True
            podcast.save()

            request.user.subscriptions.create(podcast=podcast)

            messages.success(
                request,
                "Podcast added to your Private Feeds and will appear here soon",
            )
            return redirect("private_feeds:index")
    else:
        form = PodcastForm()

    return render_partial_response(
        request,
        "private_feeds/private_feed_form.html",
        {"form": form},
        target="private-feed-form",
        partial="form",
    )


@require_DELETE
@login_required
def remove_private_feed(
    request: AuthenticatedHttpRequest,
    podcast_id: int,
) -> HttpResponseRedirect:
    """Delete private feed."""

    get_object_or_404(
        Podcast.objects.published().filter(private=True).subscribed(request.user),
        pk=podcast_id,
    ).delete()

    messages.info(request, "Removed from Private Feeds")
    return redirect("private_feeds:index")
