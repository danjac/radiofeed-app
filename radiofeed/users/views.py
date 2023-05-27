import contextlib

from django.contrib import messages
from django.contrib.auth import logout
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe
from django_htmx.http import HttpResponseClientRedirect

from radiofeed.decorators import require_auth, require_form_methods
from radiofeed.pagination import render_pagination_response
from radiofeed.podcasts.models import Podcast
from radiofeed.users.forms import OpmlUploadForm, PrivateFeedForm, UserPreferencesForm


@require_form_methods
@require_auth
def user_preferences(request: HttpRequest) -> HttpResponse:
    """Allow user to edit their preferences."""
    form = UserPreferencesForm(request.POST or None, instance=request.user)

    if request.method == "POST" and form.is_valid():
        form.save()

        messages.success(request, "Your preferences have been saved")

    return render(request, "account/preferences.html", {"form": form})


@require_safe
@require_auth
def manage_podcast_feeds(request: HttpRequest) -> HttpResponse:
    """Renders import/export page."""
    return render(request, "account/podcast_feeds.html", {"form": OpmlUploadForm()})


@require_POST
@require_auth
def import_podcast_feeds(request: HttpRequest) -> HttpResponse:
    """Imports an OPML document and subscribes user to any discovered feeds."""
    form = OpmlUploadForm(request.POST, request.FILES)
    if form.is_valid():
        if new_feeds := form.subscribe_to_feeds(request.user):
            messages.success(
                request,
                f"{new_feeds} podcast feed{pluralize(new_feeds)} added to your collection",  # noqa
            )
        else:
            messages.info(request, "No new podcasts found in uploaded file")

    return render(request, "account/podcast_feeds.html", {"form": form})


@require_POST
@require_auth
def export_podcast_feeds(request: HttpRequest) -> HttpResponse:
    """Download OPML document containing feeds from user's subscriptions."""
    podcasts = (
        Podcast.objects.filter(
            subscriptions__subscriber=request.user,
            private=False,
        )
        .distinct()
        .order_by("title")
        .iterator()
    )

    response = render(
        request,
        "account/podcasts.opml",
        {
            "podcasts": podcasts,
        },
        content_type="text/x-opml",
    )
    response[
        "Content-Disposition"
    ] = f"attachment; filename=podcasts-{timezone.now().strftime('%Y-%m-%d')}.opml"
    return response


@require_safe
@require_auth
def user_stats(request: HttpRequest) -> HttpResponse:
    """Render user statistics including listening history, subscriptions, etc."""
    return render(request, "account/stats.html")


@require_safe
@require_auth
def private_feeds(request: HttpRequest) -> HttpResponse:
    """Lists user's private feeds."""
    podcasts = Podcast.objects.filter(
        private=True,
        pub_date__isnull=False,
        pk__in=set(
            request.user.subscriptions.values_list(
                "podcast",
                flat=True,
            )
        ),
    ).order_by("-pub_date")

    return render_pagination_response(
        request,
        podcasts,
        "account/private_feeds.html",
        "podcasts/_podcasts.html",
        {"form": PrivateFeedForm()},
    )


@require_POST
@require_auth
def add_private_feed(request: HttpRequest) -> HttpResponse:
    """Add new private feed to collection."""
    form = PrivateFeedForm(request.POST)
    if form.is_valid():
        podcast = form.save()

        with contextlib.suppress(IntegrityError):
            request.user.subscriptions.create(podcast=podcast)

        message = (
            "Podcast has been added to your private feeds."
            if podcast.pub_date
            else "Podcast should appear in your private feeds in a few minutes."
        )

        messages.success(request, message)

        return HttpResponseClientRedirect(reverse("users:private_feeds"))

    return render(request, "account/_private_feed_form.html", {"form": form})


@require_POST
@require_auth
def remove_private_feed(request: HttpRequest, podcast_id: int) -> HttpResponse:
    """Removes subscription to private feed."""
    podcast = get_object_or_404(Podcast, private=True, pk=podcast_id)
    request.user.subscriptions.filter(podcast=podcast).delete()
    messages.info(request, "Podcast has been removed from your private feeds.")
    return redirect(reverse("users:private_feeds"))


@require_form_methods
@require_auth
def delete_account(request: HttpRequest) -> HttpResponse:
    """Delete account on confirmation.

    Returns:
         redirect to index page on delete confirmation, otherwise render delete
         confirmation page.
    """
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return redirect("podcasts:landing_page")
    return render(request, "account/delete_account.html")
