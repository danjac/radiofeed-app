from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect
from django.template.defaultfilters import pluralize
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_safe

from radiofeed.http import require_form_methods
from radiofeed.users.forms import OpmlUploadForm, UserPreferencesForm


@require_form_methods
@login_required
def user_preferences(
    request: HttpRequest,
) -> HttpResponseRedirect | TemplateResponse:
    """Allow user to edit their preferences."""

    if request.method == "POST":
        form = UserPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your preferences have been saved")
            return HttpResponseRedirect(request.path)

    else:
        form = UserPreferencesForm(instance=request.user)

    return TemplateResponse(
        request,
        "account/preferences.html",
        {"form": form},
    )


@require_form_methods
@login_required
def import_podcast_feeds(
    request: HttpRequest,
) -> HttpResponseRedirect | TemplateResponse:
    """Imports an OPML document and subscribes user to any discovered feeds."""
    if request.method == "POST":
        form = OpmlUploadForm(request.POST, request.FILES)
        if form.is_valid():
            if num_new_feeds := len(form.subscribe_to_feeds(request.user)):
                messages.success(
                    request,
                    f"{num_new_feeds} podcast feed{pluralize(num_new_feeds)} added to your collection",
                )
            else:
                messages.info(request, "No new podcasts found in uploaded file")

            return HttpResponseRedirect(request.path)
    else:
        form = OpmlUploadForm()

    return TemplateResponse(
        request,
        "account/podcast_feeds.html",
        {
            "upload_form": form,
        },
    )


@require_safe
@login_required
def export_podcast_feeds(request: HttpRequest) -> TemplateResponse:
    """Download OPML document containing public feeds from user's subscriptions."""

    subscriptions = (
        request.user.subscriptions.filter(
            podcast__private=False,
            podcast__pub_date__isnull=False,
        )
        .select_related("podcast")
        .order_by("podcast__title")
    )

    return TemplateResponse(
        request,
        "account/podcasts.opml",
        {
            "subscriptions": subscriptions,
        },
        content_type="text/x-opml",
        headers={
            "Content-Disposition": f"attachment; filename=podcasts-{timezone.now().strftime('%Y-%m-%d')}.opml"
        },
    )


@require_safe
@login_required
def user_stats(request: HttpRequest) -> TemplateResponse:
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
    return TemplateResponse(request, "account/stats.html", {"stats": stats})


@require_form_methods
@login_required
def delete_account(request: HttpRequest) -> HttpResponseRedirect | TemplateResponse:
    """Delete account on confirmation."""
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return HttpResponseRedirect(reverse("podcasts:index"))
    return TemplateResponse(request, "account/delete_account.html")
