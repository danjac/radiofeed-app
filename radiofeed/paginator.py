from django.conf import settings
from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.utils.functional import SimpleLazyObject


def paginate(
    request: HttpRequest,
    object_list: QuerySet,
    page_size: int = settings.PAGE_SIZE,
    param: str = "page",
    **pagination_kwargs,
) -> Page:
    """Returns paginated object list."""
    return Paginator(object_list, page_size).get_page(
        request.GET.get(param, ""), **pagination_kwargs
    )


def paginate_lazy(*args, **kwargs) -> SimpleLazyObject:
    """Returns lazily-evaluated pagination object"""
    return SimpleLazyObject(lambda: paginate(*args, **kwargs))


def render_paginated_response(
    request: HttpRequest,
    template_name: str,
    object_list: QuerySet,
    extra_context: dict | None = None,
    **pagination_kwargs,
) -> TemplateResponse:
    """Returns response with lazily-evaluated Page object as `page_obj` in template."""
    return TemplateResponse(
        request,
        template_name,
        {
            "page_obj": paginate_lazy(
                request,
                object_list,
                **pagination_kwargs,
            )
        }
        | (extra_context or {}),
    )