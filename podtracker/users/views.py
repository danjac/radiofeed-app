from __future__ import annotations

import csv

from typing import Generator

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from podtracker.episodes.models import AudioLog, Bookmark
from podtracker.podcasts.models import Podcast, Subscription
from podtracker.users.forms import UserPreferencesForm


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
        "account/includes/preferences.html"
        if request.htmx.target == target
        else "account/preferences.html",
        {
            "form": form,
            "target": target,
        },
    )


@require_http_methods(["GET"])
@login_required
def export_podcast_feeds(request: HttpRequest) -> HttpResponse:

    return TemplateResponse(
        request,
        "account/export_podcast_feeds.html",
        {
            "formats": [
                ("csv", "table", reverse("users:export_podcast_feeds_csv")),
                ("json", "code", reverse("users:export_podcast_feeds_json")),
                ("opml", "rss", reverse("users:export_podcast_feeds_opml")),
            ]
        },
    )


@require_http_methods(["GET"])
@login_required
def export_podcast_feeds_csv(request: HttpRequest) -> HttpResponse:

    response = HttpResponse(content_type="text/csv")

    writer = csv.writer(response)
    writer.writerow(["Title", "RSS", "Website"])

    for podcast in get_podcasts_for_export(request):
        writer.writerow(
            [
                podcast.title,
                podcast.rss,
                podcast.link,
            ]
        )
    return with_export_response_attachment(response, "csv")


@require_http_methods(["GET"])
@login_required
def export_podcast_feeds_json(request: HttpRequest) -> HttpResponse:

    return with_export_response_attachment(
        JsonResponse(
            {
                "podcasts": [
                    {
                        "title": podcast.title,
                        "rss": podcast.rss,
                        "url": podcast.link,
                    }
                    for podcast in get_podcasts_for_export(request)
                ]
            }
        ),
        "json",
    )


@require_http_methods(["GET"])
@login_required
def export_podcast_feeds_opml(request: HttpRequest) -> HttpResponse:

    return with_export_response_attachment(
        SimpleTemplateResponse(
            "account/opml.xml",
            {"podcasts": get_podcasts_for_export(request)},
            content_type="application/xml",
        ),
        "opml",
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


def with_export_response_attachment(
    response: HttpResponse, extension: str
) -> HttpResponse:

    response[
        "Content-Disposition"
    ] = f"attachment; filename=podcasts-{timezone.now().strftime('%Y-%m-%d')}.{extension}"

    return response


def get_podcasts_for_export(request: HttpRequest) -> Generator[Podcast, None, None]:
    return (
        Podcast.objects.filter(
            subscription__user=request.user,
            pub_date__isnull=False,
        )
        .distinct()
        .order_by("title")
        .iterator()
    )
