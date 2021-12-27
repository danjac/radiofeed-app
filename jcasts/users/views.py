from __future__ import annotations

import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.response import SimpleTemplateResponse, TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from jcasts.episodes.models import AudioLog, Bookmark
from jcasts.podcasts.models import Podcast, Subscription
from jcasts.users.forms import UserPreferencesForm


@require_http_methods(["GET", "POST"])
@login_required
def user_preferences(request: HttpRequest) -> HttpResponse:

    if request.method == "POST":

        if (
            form := UserPreferencesForm(
                request.POST,
                instance=request.user,
            )
        ).is_valid():

            form.save()
            messages.success(request, "Your preferences have been saved")
            return redirect(request.path)

    else:
        form = UserPreferencesForm(instance=request.user)

    return TemplateResponse(request, "account/preferences.html", {"form": form})


@require_http_methods(["GET"])
@login_required
def export_podcast_feeds(request: HttpRequest) -> HttpResponse:

    if not (export_format := request.GET.get("format")):
        return TemplateResponse(
            request,
            "account/export_podcast_feeds.html",
            {
                "formats": (
                    ("csv", "table"),
                    ("json", "code"),
                    ("opml", "rss"),
                )
            },
        )

    try:
        renderer = {
            "csv": render_csv_export,
            "json": render_json_export,
            "opml": render_opml_export,
        }[export_format]
    except KeyError:
        raise Http404(f"format {export_format} not supported")

    response = renderer(
        Podcast.objects.filter(
            subscription__user=request.user,
            pub_date__isnull=False,
        )
        .distinct()
        .order_by("title")
        .iterator(),
    )

    response[
        "Content-Disposition"
    ] = f"attachment; filename=podcasts-{timezone.now().strftime('%Y-%m-%d')}.{export_format}"

    return response


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
        return redirect(settings.HOME_URL)
    return TemplateResponse(request, "account/delete_account.html")


def render_opml_export(podcasts: QuerySet) -> HttpResponse:
    return SimpleTemplateResponse(
        "account/opml.xml",
        {"podcasts": podcasts},
        content_type="application/xml",
    )


def render_json_export(podcasts: QuerySet) -> HttpResponse:
    return JsonResponse(
        {
            "podcasts": [
                {
                    "title": podcast.title,
                    "rss": podcast.rss,
                    "url": podcast.link,
                }
                for podcast in podcasts
            ]
        }
    )


def render_csv_export(podcasts: QuerySet) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    writer = csv.writer(response)
    writer.writerow(["Title", "RSS", "Website"])
    for podcast in podcasts:
        writer.writerow(
            [
                podcast.title,
                podcast.rss,
                podcast.link,
            ]
        )
    return response
