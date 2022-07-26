from __future__ import annotations

from django.conf import settings
from django.core.paginator import InvalidPage, Paginator
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render


def render_pagination_response(
    request: HttpRequest,
    object_list: QuerySet,
    template_name: str,
    pagination_template_name: str,
    extra_context: dict | None = None,
    target: str = "object-list",
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    param: str = "page",
    **pagination_kwargs,
) -> HttpResponse:
    """Creates a TemplateResponse for a paginated QuerySet or list.

    If the request has the HX-Request header and matching HTMX target,
    will select the pagination template instead
    of the default template. The pagination template should be included
    in the default template and ensure the correct hx-target is also included.

    The following items are added to the template context:

    **page_obj**: Page instance
    **pagination_template**: pagination template name
    **pagination_target**: HTMX target

    Example:

    default template:

    .. code-block:: html

        {% include pagination_template %}

    pagination template:

    .. code-block:: html

        <div id="{{ pagination_target }}">

            {% include "pagination/pagination_links.html" %}

            {% for podcast in page_obj.object_list %}
                {% include "podcasts/podcast.html" %}
            {% empty %}
                {% include "includes/empty.html" %}
            {% endfor %}

            {% include "pagination/pagination_links.html" %}
        </div>

    Raises:
        Http404: invalid page
    """
    try:
        page_obj = Paginator(object_list, page_size, **pagination_kwargs).page(
            request.GET.get(param, 1)
        )
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
        }
        | (extra_context or {}),
    )
