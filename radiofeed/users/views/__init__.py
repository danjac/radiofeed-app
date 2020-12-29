# Standard Library
import datetime

# Django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

# Third Party Libraries
from turbo_response import Action, TurboStreamResponse, TurboStreamTemplateResponse

# Local
from ..forms import UserPreferencesForm


@login_required
def user_preferences(request):

    if request.method == "POST":
        form = UserPreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your preferences have been saved")
            return redirect(request.path)

        return TurboStreamTemplateResponse(
            request,
            "account/_preferences.html",
            {"form": form},
            action="update",
            target="prefs-form",
        )

    form = UserPreferencesForm(instance=request.user)
    return TemplateResponse(
        request, "account/preferences.html", {"form": form, "target": "prefs-form"},
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
    response = TurboStreamResponse(action=Action.REMOVE, target="accept-cookies")
    response.set_cookie(
        "accept-cookies",
        value="true",
        expires=timezone.now() + datetime.timedelta(days=30),
        samesite="Lax",
    )
    return response
