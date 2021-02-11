from typing import Dict, Optional

from django.conf import settings
from django.core.paginator import InvalidPage, Paginator
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.utils.translation import gettext as _

from turbo_response import TurboFrame


def paginate(
    request: HttpRequest,
    queryset: QuerySet,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    param: str = "page",
    allow_empty: bool = True,
    orphans: int = 0,
):

    paginator = Paginator(
        queryset, page_size, allow_empty_first_page=allow_empty, orphans=orphans
    )
    try:
        return paginator.page(int(request.GET.get(param, 1)))
    except (ValueError, InvalidPage):
        raise Http404(_("Invalid page"))


def render_paginated_response(
    request: HttpRequest,
    queryset: QuerySet,
    template_name: str,
    extra_context: Optional[Dict] = None,
    **pagination_kwargs
) -> HttpResponse:
    return (
        TurboFrame(request.turbo.frame)
        .template(
            template_name,
            {
                "page_obj": paginate(request, queryset, **pagination_kwargs),
                **(extra_context or {}),
            },
        )
        .response(request)
    )
