from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_safe

from simplecasts.http.request import HttpRequest
from simplecasts.http.response import RenderOrRedirectResponse
from simplecasts.models import Podcast
from simplecasts.views.paginator import render_paginated_response


@require_safe
@login_required
def search_people(request: HttpRequest) -> RenderOrRedirectResponse:
    """Search all podcasts by owner(s). Redirects to discover page if no owner is given."""

    if request.search:
        results = (
            Podcast.objects.published()
            .filter(private=False)
            .search(
                request.search.value,
                "owner_search_document",
            )
        ).order_by("-rank", "-pub_date")
        return render_paginated_response(
            request,
            "search/search_people.html",
            results,
        )

    return redirect("podcasts:discover")
