from django.contrib import messages
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.defaultfilters import pluralize
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_safe
from django_htmx.http import HttpResponseLocation

from radiofeed.decorators import require_auth, require_form_methods
from radiofeed.forms import handle_form
from radiofeed.htmx import render_blocks_to_response
from radiofeed.users.forms import OpmlUploadForm, UserPreferencesForm


@require_form_methods
@require_auth
def user_preferences(request: HttpRequest) -> HttpResponse:
    """Allow user to edit their preferences."""

    form, result = handle_form(UserPreferencesForm, request, instance=request.user)

    if result:
        form.save()
        messages.success(request, "Your preferences have been saved")
        return HttpResponseLocation(request.path)

    return render_blocks_to_response(
        request,
        "account/preferences.html",
        {"form": form},
        use_blocks="form",
        target="preferences-form",
        status=result.status,
    )


@require_safe
@require_auth
def manage_podcast_feeds(request: HttpRequest) -> TemplateResponse:
    """Renders import/export page."""
    return TemplateResponse(
        request,
        "account/podcast_feeds.html",
        {
            "upload_form": OpmlUploadForm(),
        },
    )


@require_POST
@require_auth
def import_podcast_feeds(
    request: HttpRequest,
) -> HttpResponse:
    """Imports an OPML document and subscribes user to any discovered feeds."""
    form, result = handle_form(OpmlUploadForm, request)
    if result:
        if num_new_feeds := len(form.subscribe_to_feeds(request.user)):
            messages.success(
                request,
                f"{num_new_feeds} podcast feed{pluralize(num_new_feeds)} added to your collection",
            )
        else:
            messages.info(request, "No new podcasts found in uploaded file")

        return HttpResponseLocation(reverse("users:manage_podcast_feeds"))

    return render_blocks_to_response(
        request,
        "account/podcast_feeds.html",
        {
            "upload_form": form,
        },
        use_blocks="import_feeds_form",
        target="import-feeds-form",
        status=result.status,
    )


@require_safe
@require_auth
def export_podcast_feeds(request: HttpRequest) -> TemplateResponse:
    """Download OPML document containing public feeds from user's subscriptions."""

    subscriptions = (
        request.user.subscriptions.filter(podcast__private=False)
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
@require_auth
def user_stats(request: HttpRequest) -> TemplateResponse:
    """Render user statistics including listening history, subscriptions, etc."""
    return TemplateResponse(request, "account/stats.html")


@require_form_methods
@require_auth
def delete_account(request: HttpRequest) -> HttpResponse:
    """Delete account on confirmation."""
    if request.method == "POST" and "confirm-delete" in request.POST:
        request.user.delete()
        logout(request)
        messages.info(request, "Your account has been deleted")
        return HttpResponseRedirect(reverse("podcasts:landing_page"))
    return TemplateResponse(request, "account/delete_account.html")
