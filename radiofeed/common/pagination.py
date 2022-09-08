from __future__ import annotations

from typing import Iterable

from django.core.paginator import InvalidPage, Paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render


def render_pagination_response(
    request: HttpRequest,
    object_list: Iterable,
    template_name: str,
    pagination_template_name: str,
    extra_context: dict | None = None,
    target: str = "object-list",
    param: str = "page",
    page_size: int = 30,
    **pagination_kwargs,
) -> HttpResponse:
    """Renders paginated response.

    Raises:
        Http404: invalid page
    """
    try:
        page_obj = Paginator(
            object_list,
            page_size,
            **pagination_kwargs,
        ).page(request.GET.get(param, 1))
    except InvalidPage:
        raise Http404()

    return render(
        request,
        pagination_template_name
        if request.htmx and request.htmx.target == target
        else template_name,
        {
            "page_obj": page_obj,
            "pagination_target": target,
            "pagination_template": pagination_template_name,
            **(extra_context or {}),
        },
    )
