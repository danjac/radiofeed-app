import csv
import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from turbo_response import TurboStream, redirect_303, render_form_response

from audiotrails.episodes.models import AudioLog, Favorite, QueueItem
from audiotrails.podcasts.models import Follow, Podcast

from .forms import UserPreferencesForm


@login_required
def user_preferences(request):
    if request.method == "POST":
        form = UserPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your preferences have been saved")
            return redirect_303(request.path)
    else:
        form = UserPreferencesForm(instance=request.user)

    return render_form_response(
        request,
        form,
        "account/preferences.html",
    )


@login_required
def export_podcast_feeds(request):
    if request.method != "POST":
        return TemplateResponse(request, "account/export_podcast_feeds.html")
    # set a max limit of 500 for now to prevent a DOS attack
    podcasts = (
        Podcast.objects.filter(follow__user=request.user, pub_date__isnull=False)
        .distinct()
        .order_by("-pub_date")
    )[:500]

    filename = f"podcasts-{timezone.now().strftime('%Y-%m-%d')}"

    if request.POST.get("format") == "opml":
        response = TemplateResponse(
            request,
            "account/opml.xml",
            {"podcasts": podcasts},
            content_type="application/xml",
        )
        response["Content-Disposition"] = f"attachment; filename={filename}.xml"
    else:
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
                    podcast.pub_date.strftime("%Y-%m-%d"),
                ]
            )
    return response


@login_required
def user_stats(request):

    logs = AudioLog.objects.filter(user=request.user)
    follows = Follow.objects.filter(user=request.user)
    favorites = Favorite.objects.filter(user=request.user)
    queue_items = QueueItem.objects.filter(user=request.user)

    return TemplateResponse(
        request,
        "account/stats.html",
        {
            "stats": {
                "listened": logs.count(),
                "in_progress": logs.filter(completed__isnull=True).count(),
                "completed": logs.filter(completed__isnull=False).count(),
                "follows": follows.count(),
                "in_queue": queue_items.count(),
                "favorites": favorites.count(),
            },
        },
    )


@login_required
def delete_account(request):
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return redirect(settings.HOME_URL)
    return TemplateResponse(request, "account/delete_account.html")


@require_POST
def accept_cookies(request):
    response = (
        TurboStream("accept-cookies").remove.response()
        if request.turbo
        else redirect(get_redirect_url(request))
    )
    response.set_cookie(
        "accept-cookies",
        value="true",
        expires=timezone.now() + datetime.timedelta(days=30),
        samesite="Lax",
    )
    return response


def get_redirect_url(
    request,
    redirect_url_param="redirect_url",
    default_url=settings.HOME_URL,
):
    redirect_url = request.POST.get(redirect_url_param)
    if redirect_url and url_has_allowed_host_and_scheme(
        redirect_url, {request.get_host()}, request.is_secure()
    ):
        return redirect_url
    return default_url
