from __future__ import annotations

from django.conf import settings
from django.core.paginator import InvalidPage, Page, Paginator
from django.db.models import QuerySet
from django.http import Http404, HttpRequest
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _


def paginate(
    request: HttpRequest,
    object_list: list | QuerySet,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    param: str = "page",
    allow_empty: bool = True,
    orphans: int = 0,
) -> Page:

    paginator = Paginator(
        object_list,
        page_size,
        allow_empty_first_page=allow_empty,
        orphans=orphans,
    )
    try:
        return paginator.page(int(request.GET.get(param, 1)))
    except (ValueError, InvalidPage):
        raise Http404(_("Invalid page"))


def render_paginated_response(
    request: HttpRequest,
    object_list: list | QuerySet,
    template_name: str,
    extra_context: dict | None = None,
    **pagination_kwargs,
) -> TemplateResponse:
    page_obj = paginate(request, object_list, **pagination_kwargs)
    context = {
        "page_obj": page_obj,
        **(extra_context or {}),
    }
    return TemplateResponse(request, template_name, context)
