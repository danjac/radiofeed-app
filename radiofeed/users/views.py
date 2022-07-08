from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_http_methods

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.forms import OpmlUploadForm, UserPreferencesForm


@require_http_methods(["GET", "POST"])
@login_required
def user_preferences(
    request: HttpRequest, target: str = "preferences-form"
) -> TemplateResponse:
    """Handle user preferences."""
    form = UserPreferencesForm(request.POST or None, instance=request.user)

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(request, _("Your preferences have been saved"))

    return TemplateResponse(
        request,
        "account/forms/preferences.html"
        if request.htmx.target == target
        else "account/preferences.html",
        {
            "form": form,
            "target": target,
        },
    )


@require_http_methods(["GET"])
@login_required
def import_export_podcast_feeds(request: HttpRequest) -> TemplateResponse:
    """Renders import/export page."""
    return TemplateResponse(
        request,
        "account/import_export_podcast_feeds.html",
        {
            "form": OpmlUploadForm(),
            "target": "opml-import-form",
        },
    )


@require_http_methods(["POST"])
@login_required
def import_podcast_feeds(
    request: HttpRequest, target: str = "opml-import-form"
) -> TemplateResponse:
    """Imports an OPML document and subscribes user to any discovered feeds."""
    form = OpmlUploadForm(request.POST, request.FILES)
    if form.is_valid():

        if new_feeds := form.subscribe_to_feeds(request.user):
            messages.success(
                request,
                ngettext(
                    "%(count)d podcast feed added to your collection",
                    "%(count)d podcast feeds added to your collection",
                    new_feeds,
                )
                % {"count": new_feeds},
            )
        else:
            messages.info(request, _("No new podcasts found in uploaded file"))

    return TemplateResponse(
        request,
        "account/forms/import_podcast_feeds.html"
        if request.htmx.target == target
        else "account/import_export_podcast_feeds.html",
        {
            "form": form,
            "target": target,
        },
    )


@require_http_methods(["POST"])
@login_required
def export_podcast_feeds(request: HttpRequest) -> SimpleTemplateResponse:
    """Download OPML document containing feeds from user's subscriptions."""
    podcasts = (
        Podcast.objects.filter(
            subscription__user=request.user,
        )
        .distinct()
        .order_by("title")
        .iterator()
    )

    return SimpleTemplateResponse(
        "account/podcasts.opml",
        {"podcasts": podcasts},
        content_type="text/x-opml",
        headers={
            "Content-Disposition": f"attachment; filename=podcasts-{timezone.now().strftime('%Y-%m-%d')}.opml"
        },
    )


@require_http_methods(["GET"])
@login_required
def user_stats(request: HttpRequest) -> TemplateResponse:
    """Render user statistics including listening history, subscriptions, etc."""
    logs = AudioLog.objects.filter(user=request.user)

    return TemplateResponse(
        request,
        "account/stats.html",
        {
            "stats": {
                "listened": logs.count(),
                "subscribed": Subscription.objects.filter(user=request.user).count(),
                "bookmarks": Bookmark.objects.filter(user=request.user).count(),
            },
        },
    )


@require_http_methods(["GET", "POST"])
@login_required
def delete_account(request: HttpRequest) -> HttpResponseRedirect | TemplateResponse:
    """Delete account on confirmation.

    Returns:
         redirect to index page on delete confirmation, otherwise render delete confirmation page.
    """
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, _("Your account has been deleted"))
        return HttpResponseRedirect(settings.HOME_URL)
    return TemplateResponse(request, "account/delete_account.html")
