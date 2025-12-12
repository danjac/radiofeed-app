import itertools
from typing import TypedDict

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_safe

from listenwave.feedparser.opml_parser import parse_opml
from listenwave.http import require_form_methods
from listenwave.partials import render_partial_response
from listenwave.podcasts.models import Podcast, Subscription
from listenwave.request import (
    AuthenticatedHttpRequest,
    HttpRequest,
    is_authenticated_request,
)
from listenwave.response import RenderOrRedirectResponse
from listenwave.users.emails import get_unsubscribe_signer
from listenwave.users.forms import (
    AccountDeletionConfirmationForm,
    OpmlUploadForm,
    UserPreferencesForm,
)


class UserStat(TypedDict):
    """Line item in user stats"""

    label: str
    value: int
    unit: str
    url: str


@require_form_methods
@login_required
def user_preferences(request: AuthenticatedHttpRequest) -> RenderOrRedirectResponse:
    """Allow user to edit their preferences."""
    if request.method == "POST":
        form = UserPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your preferences have been saved")
            return HttpResponseRedirect(reverse("users:preferences"))
    else:
        form = UserPreferencesForm(instance=request.user)

    return render_partial_response(
        request,
        "account/preferences.html",
        {"form": form},
        target="preferences-form",
        partial="form",
    )


@require_form_methods
@login_required
def import_podcast_feeds(
    request: AuthenticatedHttpRequest, feed_limit: int = 360
) -> RenderOrRedirectResponse:
    """Imports an OPML document and subscribes user to any discovered feeds."""
    if request.method == "POST":
        form = OpmlUploadForm(request.POST, request.FILES)
        if form.is_valid():
            opml = form.cleaned_data["opml"]
            opml.seek(0)

            feeds = itertools.islice(parse_opml(opml.read()), feed_limit)
            podcasts = Podcast.objects.filter(active=True, private=False, rss__in=feeds)

            Subscription.objects.bulk_create(
                (
                    Subscription(subscriber=request.user, podcast=podcast)
                    for podcast in podcasts
                ),
                ignore_conflicts=True,
            )

            messages.success(request, "You have been subscribed to new podcast feeds.")
            return HttpResponseRedirect(reverse("users:import_podcast_feeds"))
    else:
        form = OpmlUploadForm()

    return render_partial_response(
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
def export_podcast_feeds(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Download OPML document containing public feeds from user's subscriptions."""

    podcasts = (
        Podcast.objects.published()
        .subscribed(request.user)
        .filter(
            private=False,
        )
        .order_by("-pub_date")
    )

    filename = f"podcasts-{timezone.now().strftime('%Y-%m-%d')}.opml"

    return TemplateResponse(
        request,
        "feedparser/podcasts.opml",
        {
            "site": request.site,
            "podcasts": podcasts,
        },
        content_type="text/x-opml",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@require_safe
@login_required
def user_stats(request: AuthenticatedHttpRequest) -> TemplateResponse:
    """Render user statistics including listening history, subscriptions, etc."""
    subscriptions = request.user.subscriptions.filter(podcast__pub_date__isnull=False)
    stats = [
        UserStat(
            label="Subscribed",
            value=subscriptions.count(),
            unit="podcast",
            url=reverse("podcasts:subscriptions"),
        ),
        UserStat(
            label="Private Feeds",
            value=subscriptions.filter(podcast__private=True).count(),
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
    return TemplateResponse(request, "account/stats.html", {"stats": stats})


@require_safe
def unsubscribe(
    request: HttpRequest, timeout: int = 24 * 60 * 60
) -> HttpResponseRedirect:
    """Unsubscribe user from email notifications.

    The email address should be an encrypted token. Look up the EmailAddress instance and the user,
    and uncheck their `send_email_notifications` flag.

    Redirect to the index page with a success message.
    """

    try:
        email = get_unsubscribe_signer().unsign(request.GET["email"], max_age=timeout)
        qs = EmailAddress.objects.filter(user__is_active=True).select_related("user")
        if request.user.is_authenticated:
            qs = qs.filter(user=request.user)
        user = qs.get(email=email).user
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

    redirect_url = (
        reverse("users:preferences")
        if request.user.is_authenticated
        else reverse("index")
    )

    return HttpResponseRedirect(redirect_url)


@require_form_methods
def delete_account(request: HttpRequest) -> RenderOrRedirectResponse:
    """Delete account on confirmation."""
    if is_authenticated_request(request):
        if request.method == "POST":
            form = AccountDeletionConfirmationForm(request.POST)
            if form.is_valid():
                request.user.delete()
                logout(request)
                messages.info(request, "Your account has been deleted")
                return HttpResponseRedirect(reverse("index"))
        else:
            form = AccountDeletionConfirmationForm()
    else:
        form = None

    return TemplateResponse(request, "account/delete_account.html", {"form": form})
