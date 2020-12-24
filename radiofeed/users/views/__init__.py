# Django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.template.response import TemplateResponse

# RadioFeed
from radiofeed.common.turbo.response import TurboStreamResponse

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

        return TurboStreamResponse(
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
