from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe

from radiofeed.http import require_form_methods
from radiofeed.users.forms import OpmlUploadForm, UserPreferencesForm


@require_form_methods
@login_required
def user_preferences(
    request: HttpRequest,
) -> HttpResponse:
    """Allow user to edit their preferences."""

    if request.method == "POST":
        form = UserPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your preferences have been saved")

            return redirect(request.path)

    else:
        form = UserPreferencesForm(instance=request.user)

    return render(
        request,
        "account/preferences.html",
        {"form": form},
    )


@require_safe
@login_required
def manage_podcast_feeds(request: HttpRequest) -> HttpResponse:
    """Renders import/export page."""
    return render(
        request,
        "account/podcast_feeds.html",
        {
            "upload_form": OpmlUploadForm(),
        },
    )


@require_POST
@login_required
def import_podcast_feeds(
    request: HttpRequest,
) -> HttpResponse:
    """Imports an OPML document and subscribes user to any discovered feeds."""
    form = OpmlUploadForm(request.POST, request.FILES)
    if form.is_valid():
        if num_new_feeds := len(form.subscribe_to_feeds(request.user)):
            messages.success(
                request,
                f"{num_new_feeds} podcast feed{pluralize(num_new_feeds)} added to your collection",
            )
        else:
            messages.info(request, "No new podcasts found in uploaded file")

        return redirect("users:manage_podcast_feeds")

    return render(
        request,
        "account/podcast_feeds.html#import_feeds_form",
        {
            "upload_form": form,
        },
    )


@require_safe
@login_required
def export_podcast_feeds(request: HttpRequest) -> HttpResponse:
    """Download OPML document containing public feeds from user's subscriptions."""

    subscriptions = (
        request.user.subscriptions.filter(
            podcast__private=False,
            podcast__pub_date__isnull=False,
        )
        .select_related("podcast")
        .order_by("podcast__title")
    )

    response = render(
        request,
        "account/podcasts.opml",
        {
            "subscriptions": subscriptions,
        },
        content_type="text/x-opml",
    )
    response["Content-Disposition"] = (
        f"attachment; filename=podcasts-{timezone.now().strftime('%Y-%m-%d')}.opml"
    )
    return response


@require_safe
@login_required
def user_stats(request: HttpRequest) -> HttpResponse:
    """Render user statistics including listening history, subscriptions, etc."""
    stats = [
        {
            "label": "Subscribed",
            "value": request.user.subscriptions.count(),
            "unit": "podcast",
            "url": reverse("podcasts:index"),
        },
        {
            "label": "Private Feeds",
            "value": request.user.subscriptions.filter(podcast__private=True).count(),
            "unit": "podcast",
            "url": reverse("podcasts:private_feeds"),
        },
        {
            "label": "Bookmarks",
            "value": request.user.bookmarks.count(),
            "unit": "episode",
            "url": reverse("episodes:bookmarks"),
        },
        {
            "label": "Listened",
            "value": request.user.audio_logs.count(),
            "unit": "episode",
            "url": reverse("episodes:history"),
        },
    ]
    return render(request, "account/stats.html", {"stats": stats})


@require_form_methods
@login_required
def delete_account(request: HttpRequest) -> HttpResponse:
    """Delete account on confirmation."""
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return redirect("podcasts:index")
    return render(request, "account/delete_account.html")
