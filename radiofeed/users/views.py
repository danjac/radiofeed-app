from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from radiofeed.episodes.models import AudioLog, Bookmark
from radiofeed.podcasts.models import Podcast, Subscription
from radiofeed.users.forms import OpmlUploadForm, UserPreferencesForm


@require_http_methods(["GET", "POST"])
@login_required
def user_preferences(
    request: HttpRequest, target: str = "preferences-form"
) -> HttpResponse:

    form = UserPreferencesForm(request.POST or None, instance=request.user)

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(request, "Your preferences have been saved")

    return TemplateResponse(
        request,
        "account/partials/preferences.html"
        if request.htmx.target == target
        else "account/preferences.html",
        {
            "form": form,
            "target": target,
        },
    )


@require_http_methods(["GET"])
@login_required
def import_export_podcast_feeds(request: HttpRequest) -> HttpResponse:
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
def export_podcast_feeds(request: HttpRequest) -> HttpResponse:
    podcasts = (
        Podcast.objects.filter(
            subscription__user=request.user,
        )
        .distinct()
        .order_by("title")
        .iterator()
    )

    return SimpleTemplateResponse(
        "account/opml.xml",
        {"podcasts": podcasts},
        content_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename=podcasts-{timezone.now().strftime('%Y-%m-%d')}.opml"
        },
    )


@require_http_methods(["POST"])
@login_required
def import_podcast_feeds(
    request: HttpRequest, target: str = "opml-import-form"
) -> HttpResponse:
    form = OpmlUploadForm(request.POST, request.FILES)
    if form.is_valid():

        new_feeds: int = 0

        if feeds := form.parse_opml_feeds():

            podcasts = Podcast.objects.filter(rss__in=set(feeds)).exclude(
                subscription__user=request.user
            )
            if podcasts.exists():

                subscriptions = Subscription.objects.bulk_create(
                    [
                        Subscription(podcast=podcast, user=request.user)
                        for podcast in podcasts
                    ],
                    ignore_conflicts=True,
                )
                new_feeds = len(subscriptions)

        if new_feeds:
            messages.success(request, f"{new_feeds} podcasts added to your collection")
        else:
            messages.info(request, "No new podcasts found in uploaded file")

    return TemplateResponse(
        request,
        "account/partials/import_podcast_feeds.html"
        if request.htmx.target == target
        else "account/import_export_podcast_feeds.html",
        {
            "form": form,
            "target": target,
        },
    )


@require_http_methods(["GET"])
@login_required
def user_stats(request: HttpRequest) -> HttpResponse:

    logs = AudioLog.objects.filter(user=request.user)

    return TemplateResponse(
        request,
        "account/stats.html",
        {
            "stats": {
                "listened": logs.count(),
                "in_progress": logs.filter(completed__isnull=True).count(),
                "completed": logs.filter(completed__isnull=False).count(),
                "subscribed": Subscription.objects.filter(user=request.user).count(),
                "bookmarks": Bookmark.objects.filter(user=request.user).count(),
            },
        },
    )


@require_http_methods(["GET", "POST"])
@login_required
def delete_account(request: HttpRequest) -> HttpResponse:
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return HttpResponseRedirect(settings.HOME_URL)
    return TemplateResponse(request, "account/delete_account.html")
