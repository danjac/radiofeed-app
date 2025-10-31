from typing import TypedDict

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.signing import BadSignature
from django.http import HttpRequest, HttpResponseRedirect
from django.template.defaultfilters import pluralize
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_safe

from radiofeed.form_handler import handle_form
from radiofeed.http import require_form_methods
from radiofeed.partials import render_partial_response
from radiofeed.podcasts.models import Podcast
from radiofeed.users.emails import get_unsubscribe_signer
from radiofeed.users.forms import OpmlUploadForm, UserPreferencesForm


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
) -> TemplateResponse | HttpResponseRedirect:
    """Allow user to edit their preferences."""
    if result := handle_form(UserPreferencesForm, request, instance=request.user):
        result.form.save()
        messages.success(request, "Your preferences have been saved")
        return HttpResponseRedirect(reverse("users:preferences"))

    return render_partial_response(
        request,
        "account/preferences.html",
        {
            "form": result.form,
        },
        target="preferences-form",
        partial="form",
    )


@require_form_methods
@login_required
def import_podcast_feeds(
    request: HttpRequest,
) -> TemplateResponse | HttpResponseRedirect:
    """Imports an OPML document and subscribes user to any discovered feeds."""
    if result := handle_form(OpmlUploadForm, request):
        if num_new_feeds := len(result.form.subscribe_to_feeds(request.user)):
            messages.success(
                request,
                f"{num_new_feeds} podcast feed{pluralize(num_new_feeds)} added to your collection",
            )
        else:
            messages.info(request, "No new podcasts found in uploaded file")
        return HttpResponseRedirect(reverse("users:import_podcast_feeds"))

    return render_partial_response(
        request,
        "account/podcast_feeds.html",
        {
            "upload_form": result.form,
        },
        target="import-feeds-form",
        partial="form",
    )


@require_safe
@login_required
def export_podcast_feeds(request: HttpRequest) -> TemplateResponse:
    """Download OPML document containing public feeds from user's subscriptions."""

    podcasts = (
        Podcast.objects.published()
        .subscribed(request.user)
        .filter(
            private=False,
        )
        .order_by("-pub_date")
    )

    response = TemplateResponse(
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
def user_stats(request: HttpRequest) -> TemplateResponse:
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
    return TemplateResponse(request, "account/stats.html", {"stats": stats})


@require_safe
def unsubscribe(request: HttpRequest) -> HttpResponseRedirect:
    """Unsubscribe user from email notifications.

    The email address should be an encrypted token. Look up the EmailAddress instance and the user,
    and uncheck their `send_email_notifications` flag.

    Redirect to the index page with a success message.
    """

    try:
        email = get_unsubscribe_signer().unsign(
            request.GET["email"],
            max_age=settings.EMAIL_UNSUBSCRIBE_TIMEOUT,
        )
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
def delete_account(request: HttpRequest) -> TemplateResponse | HttpResponseRedirect:
    """Delete account on confirmation."""
    if (
        request.user.is_authenticated
        and request.method == "POST"
        and "confirm-delete" in request.POST
    ):
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return HttpResponseRedirect(reverse("index"))
    return TemplateResponse(request, "account/delete_account.html")
