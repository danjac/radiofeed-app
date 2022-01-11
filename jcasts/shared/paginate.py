from __future__ import annotations

from django.conf import settings
from django.core.paginator import InvalidPage, Page, Paginator
from django.db.models import QuerySet
from django.http import Http404, HttpRequest
from django.template.response import TemplateResponse


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
        raise Http404("Invalid page")


def render_paginated_list(
    request: HttpRequest,
    object_list: list | QuerySet,
    template_name: str,
    pagination_template_name: str,
    extra_context: dict | None = None,
    target: str = "object-list",
    **pagination_kwargs,
) -> TemplateResponse:
    return TemplateResponse(
        request,
        pagination_template_name
        if request.htmx and request.htmx.target == target
        else template_name,
        {
            "page_obj": paginate(
                request,
                object_list,
                **pagination_kwargs,
            ),
            "pagination_target": target,
            "pagination_template": pagination_template_name,
        }
        | (extra_context or {}),
    )
