from typing import TYPE_CHECKING, TypedDict, cast

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_safe

from radiofeed.http import require_form_methods
from radiofeed.partials import render_partial_for_target
from radiofeed.podcasts.models import Podcast
from radiofeed.users.emails import get_unsubscribe_signer
from radiofeed.users.forms import OpmlUploadForm, UserPreferencesForm

if TYPE_CHECKING:
    from radiofeed.users.models import User  # pragma: no cover


class UserStat(TypedDict):
    """Line item in user stats"""

    label: str
    value: int
    unit: str
    url: str


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
            return redirect("users:preferences")
    else:
        form = UserPreferencesForm(instance=request.user)

    return render_partial_for_target(
        request,
        "account/preferences.html",
        {
            "form": form,
        },
        target="preferences-form",
        partial="form",
    )


@require_form_methods
@login_required
def import_podcast_feeds(
    request: HttpRequest,
) -> HttpResponse:
    """Imports an OPML document and subscribes user to any discovered feeds."""
    if request.method == "POST":
        form = OpmlUploadForm(request.POST, request.FILES)
        if form.is_valid():
            if num_new_feeds := len(
                form.subscribe_to_feeds(cast("User", request.user))
            ):
                messages.success(
                    request,
                    f"{num_new_feeds} podcast feed{pluralize(num_new_feeds)} added to your collection",
                )
            else:
                messages.info(request, "No new podcasts found in uploaded file")
            return redirect("users:import_podcast_feeds")
    else:
        form = OpmlUploadForm()

    return render_partial_for_target(
        request,
        "account/podcast_feeds.html",
        {
            "upload_form": form,
        },
        target="import-feeds-form",
        partial="form",
    )


@require_safe
@login_required
def export_podcast_feeds(request: HttpRequest) -> HttpResponse:
    """Download OPML document containing public feeds from user's subscriptions."""

    podcasts = (
        Podcast.objects.published()
        .subscribed(request.user)
        .filter(
            private=False,
        )
        .order_by("-pub_date")
    )

    response = render(
        request,
        "feedparser/podcasts.opml",
        {
            "site": request.site,
            "podcasts": podcasts,
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
        UserStat(
            label="Subscribed",
            value=request.user.subscriptions.count(),
            unit="podcast",
            url=reverse("podcasts:subscriptions"),
        ),
        UserStat(
            label="Private Feeds",
            value=request.user.subscriptions.filter(podcast__private=True).count(),
            unit="podcast",
            url=reverse("podcasts:private_feeds"),
        ),
        UserStat(
            label="Bookmarks",
            value=request.user.bookmarks.count(),
            unit="episode",
            url=reverse("episodes:bookmarks"),
        ),
        UserStat(
            label="Listened",
            value=request.user.audio_logs.count(),
            unit="episode",
            url=reverse("episodes:history"),
        ),
    ]
    return render(request, "account/stats.html", {"stats": stats})


@require_safe
def unsubscribe(request: HttpRequest) -> HttpResponse:
    """Unsubscribe user from email notifications.

    The email address should be an encrypted token. Look up the EmailAddress instance and the user,
    and uncheck their `send_email_notifications` flag.

    Redirect to the index page with a success message.
    """

    try:
        email = get_unsubscribe_signer().unsign(
            request.GET["email"], max_age=48 * 60 * 60
        )
        user = (
            EmailAddress.objects.filter(user__is_active=True)
            .select_related("user")
            .get(email=email)
            .user
        )
    except (
        KeyError,
        ValueError,
        BadSignature,
        EmailAddress.DoesNotExist,
    ):
        messages.error(request, "Email address not found")
    else:
        user.send_email_notifications = False
        user.save()

        messages.success(request, "You have been unsubscribed from email notifications")

    return redirect("index")


@require_form_methods
def delete_account(request: HttpRequest) -> HttpResponse:
    """Delete account on confirmation."""
    if (
        request.user.is_authenticated
        and request.method == "POST"
        and "confirm-delete" in request.POST
    ):
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return redirect("index")
    return render(request, "account/delete_account.html")
