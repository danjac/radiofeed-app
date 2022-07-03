from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.template.defaultfilters import pluralize
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.forms import OpmlUploadForm, UserPreferencesForm


@require_http_methods(["GET", "POST"])
@login_required
def user_preferences(request, target="preferences-form"):
    """Handle user preferences.

    Args:
        request (HttpRequest)
        target (str): HTMX form target

    Returns:
        TemplateResponse
    """
    form = UserPreferencesForm(request.POST or None, instance=request.user)

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(request, "Your preferences have been saved")

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
def import_export_podcast_feeds(request):
    """Renders import/export page.

    Args:
        request (HttpRequest)

    Returns:
        TemplateResponse
    """
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
def import_podcast_feeds(request, target="opml-import-form"):
    """Imports an OPML document and subscribes user to any discovered feeds.

    Args:
        request (HttpRequest)
        target (str): HTMX form target

    Returns:
        TemplateResponse
    """
    form = OpmlUploadForm(request.POST, request.FILES)
    if form.is_valid():

        if new_feeds := form.subscribe_to_feeds(request.user):
            messages.success(
                request,
                f"{new_feeds} podcast{pluralize(new_feeds)} added to your collection",
            )
        else:
            messages.info(request, "No new podcasts found in uploaded file")

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
def export_podcast_feeds(request):
    """Download OPML document containing feeds from user's subscriptions.

    Args:
        request (HttpRequest)

    Returns:
        HttpResponse: OPML document
    """
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
def user_stats(request):
    """Render user statistics including listening history, subscriptions, etc.

    Args:
        request (HttpRequest)

    Returns:
        TemplateResponse
    """
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
def delete_account(request):
    """Delete account on confirmation.

    Args:
        request (HttpRequest)

    Returns:
        HttpResponse: redirect to index page on delete confirmation, otherwise
            render delete confirmation page.
    """
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return HttpResponseRedirect(settings.HOME_URL)
    return TemplateResponse(request, "account/delete_account.html")
