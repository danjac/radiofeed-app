from __future__ import annotations

from django.conf import settings
from django.core.paginator import InvalidPage, Page, Paginator
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _


def paginate(
    request,
    object_list,
    page_size=settings.DEFAULT_PAGE_SIZE,
    param="page",
    allow_empty=True,
    orphans=0,
) -> Page:

    paginator = Paginator(
        object_list, page_size, allow_empty_first_page=allow_empty, orphans=orphans
    )
    try:
        return paginator.page(int(request.GET.get(param, 1)))
    except (ValueError, InvalidPage):
        raise Http404(_("Invalid page"))


def render_paginated_response(
    request,
    object_list,
    template_name,
    pagination_template_name,
    extra_context=None,
    **pagination_kwargs,
):
    page_obj = paginate(request, object_list, **pagination_kwargs)
    context = {
        "page_obj": page_obj,
        "pagination_template": pagination_template_name,
        **(extra_context or {}),
    }
    if request.htmx and request.htmx.target == f"page-{page_obj.number}":
        template_name = pagination_template_name
        context["is_paginated"] = True

    return TemplateResponse(request, template_name, context)
