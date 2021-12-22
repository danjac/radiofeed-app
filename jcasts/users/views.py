import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from jcasts.episodes.models import AudioLog, Bookmark
from jcasts.podcasts.models import Follow, Podcast
from jcasts.shared.decorators import ajax_login_required
from jcasts.shared.response import HttpResponseNoContent
from jcasts.users.forms import UserPreferencesForm


@require_http_methods(["GET", "POST"])
@login_required
def user_preferences(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = UserPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your preferences have been saved")
            return redirect(request.path)
    else:
        form = UserPreferencesForm(instance=request.user)

    return TemplateResponse(request, "account/preferences.html", {"form": form})


@require_http_methods(["GET", "POST"])
@login_required
def export_podcast_feeds(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return TemplateResponse(request, "account/export_podcast_feeds.html")

    podcasts = (
        Podcast.objects.filter(
            follow__user=request.user,
            pub_date__isnull=False,
        )
        .distinct()
        .order_by("-pub_date")
    ).iterator()

    filename = f"podcasts-{timezone.now().strftime('%Y-%m-%d')}"

    if request.POST.get("format") == "opml":
        return render_opml_export_response(request, podcasts, filename)

    return render_csv_export_response(podcasts, filename)


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
                "follows": Follow.objects.filter(user=request.user).count(),
                "bookmarks": Bookmark.objects.filter(user=request.user).count(),
            },
        },
    )


@require_http_methods(["POST"])
@ajax_login_required
def toggle_autoplay(request: HttpRequest) -> HttpResponse:
    request.user.autoplay = not (request.user.autoplay)
    request.user.save(update_fields=["autoplay"])
    return HttpResponseNoContent()


@require_http_methods(["GET", "POST"])
@login_required
def delete_account(request: HttpRequest) -> HttpResponse:
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return redirect(settings.HOME_URL)
    return TemplateResponse(request, "account/delete_account.html")


def render_opml_export_response(
    request: HttpRequest, podcasts: list[Podcast], filename
) -> TemplateResponse:
    response = TemplateResponse(
        request,
        "account/opml.xml",
        {"podcasts": podcasts},
        content_type="application/xml",
    )
    response["Content-Disposition"] = f"attachment; filename={filename}.xml"
    return response


def render_csv_export_response(podcasts: list[Podcast], filename: str) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={filename}.csv"
    writer = csv.writer(response)
    writer.writerow(["Title", "RSS", "Website", "Published"])
    for podcast in podcasts:
        writer.writerow(
            [
                podcast.title,
                podcast.rss,
                podcast.link,
                podcast.pub_date.strftime("%Y-%m-%d") if podcast.pub_date else "-",
            ]
        )
    return response
