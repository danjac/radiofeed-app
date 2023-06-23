from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe
from django_htmx.http import HttpResponseLocation

from radiofeed.decorators import require_auth, require_form_methods
from radiofeed.forms import handle_form
from radiofeed.fragments import render_template_fragments
from radiofeed.podcasts.models import Podcast
from radiofeed.users.forms import OpmlUploadForm, UserPreferencesForm


@require_form_methods
@require_auth
def user_preferences(request: HttpRequest) -> HttpResponse:
    """Allow user to edit their preferences."""

    form, success = handle_form(UserPreferencesForm, request, instance=request.user)
    if success:
        form.save()
        messages.success(request, "Your preferences have been saved")

    return render(request, "account/preferences.html", {"form": form})


@require_safe
@require_auth
def manage_podcast_feeds(request: HttpRequest) -> HttpResponse:
    """Renders import/export page."""
    return render(request, "account/podcast_feeds.html", {"form": OpmlUploadForm()})


@require_POST
@require_auth
def import_podcast_feeds(request: HttpRequest) -> HttpResponse:
    """Imports an OPML document and subscribes user to any discovered feeds."""
    form, success = handle_form(OpmlUploadForm, request)
    if success:
        if new_feeds := form.subscribe_to_feeds(request.user):
            messages.success(
                request,
                f"{new_feeds} podcast feed{pluralize(new_feeds)} added to your collection",  # noqa
            )
        else:
            messages.info(request, "No new podcasts found in uploaded file")

        return HttpResponseLocation(reverse("users:manage_podcast_feeds"))

    if request.htmx.target == "import-feeds-form":
        return render_template_fragments(
            request,
            "account/podcast_feeds.html",
            {"form": form},
            use_blocks=["import_feeds_form"],
        )

    return render(request, "account/podcast_feeds.html", {"form": form})


@require_POST
@require_auth
def export_podcast_feeds(request: HttpRequest) -> HttpResponse:
    """Download OPML document containing public feeds from user's subscriptions."""
    podcasts = (
        Podcast.objects.subscribed(request.user)
        .filter(private=False)
        .distinct()
        .order_by("title")
        .iterator()
    )

    response = render(
        request,
        "account/podcasts.opml",
        {
            "podcasts": podcasts,
        },
        content_type="text/x-opml",
    )
    response[
        "Content-Disposition"
    ] = f"attachment; filename=podcasts-{timezone.now().strftime('%Y-%m-%d')}.opml"
    return response


@require_safe
@require_auth
def user_stats(request: HttpRequest) -> HttpResponse:
    """Render user statistics including listening history, subscriptions, etc."""
    return render(request, "account/stats.html")


@require_form_methods
@require_auth
def delete_account(request: HttpRequest) -> HttpResponse:
    """Delete account on confirmation.

    Returns:
         redirect to index page on delete confirmation, otherwise render delete
         confirmation page.
    """
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return redirect("podcasts:landing_page")
    return render(request, "account/delete_account.html")
