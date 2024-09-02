from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.http import HttpRequest, HttpResponseRedirect
from django.template.defaultfilters import pluralize
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_safe

from radiofeed.http import require_form_methods
from radiofeed.podcasts.models import Podcast
from radiofeed.template_partials import render_template_partial
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

    return render_template_partial(
        request,
        "account/preferences.html",
        {
            "form": form,
        },
        partial="form",
        target="preferences-form",
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

    return render_template_partial(
        request,
        "account/podcast_feeds.html",
        {
            "upload_form": form,
        },
        partial="upload_form",
        target="import-feeds-form",
    )


@require_safe
@login_required
def export_podcast_feeds(request: HttpRequest) -> TemplateResponse:
    """Download OPML document containing public feeds from user's subscriptions."""

    podcasts = (
        Podcast.objects.annotate(
            is_subscribed=Exists(
                request.user.subscriptions.filter(
                    podcast=OuterRef("pk"),
                )
            )
        )
        .filter(
            is_subscribed=True,
            private=False,
            pub_date__isnull=False,
        )
        .order_by("title")
    )

    return TemplateResponse(
        request,
        "feedparser/podcasts.opml",
        {
            "site": request.site,
            "podcasts": podcasts,
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
