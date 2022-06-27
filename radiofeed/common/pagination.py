from django.conf import settings
from django.core.paginator import InvalidPage, Paginator
from django.http import Http404
from django.template.response import TemplateResponse


def pagination_response(
    request,
    object_list,
    template_name,
    pagination_template_name,
    extra_context=None,
    target="object-list",
    page_size=settings.DEFAULT_PAGE_SIZE,
    param="page",
    **pagination_kwargs,
):
    """Renders a pagination_responsed response"""

    try:
        page_obj = Paginator(object_list, page_size, **pagination_kwargs).page(
            int(request.GET.get(param, 1))
        )
    except (ValueError, InvalidPage):
        raise Http404("Invalid page")

    return TemplateResponse(
        request,
        pagination_template_name
        if request.htmx and request.htmx.target == target
        else template_name,
        {
            "page_obj": page_obj,
            "pagination_target": target,
            "pagination_template": pagination_template_name,
        }
        | (extra_context or {}),
    )
