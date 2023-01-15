from __future__ import annotations

import dataclasses

from collections.abc import Iterable

from django.core import paginator
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render


@dataclasses.dataclass(frozen=True)
class Paginator:
    """Wraps pagination functionality."""

    request: HttpRequest

    param: str = "page"
    page_size: int = 30
    target: str = "pagination"

    def url(self, page_number: int) -> str:
        """Inserts the page query string parameter with the provided page number into the template.

        Preserves the original request path and any other query string parameters.

        Given the above and a URL of "/search?q=test" the result would
        be something like: "/search?q=test&p=3"

        Returns:
            updated URL path with new page
        """
        qs = self.request.GET.copy()
        qs[self.param] = page_number
        return f"{self.request.path}?{qs.urlencode()}"

    def render(
        self,
        object_list: Iterable,
        template_name: str,
        pagination_template_name: str,
        extra_context: dict | None = None,
    ) -> HttpResponse:
        """Renders paginated response.

        Raises:
            Http404: invalid page number
        """
        try:
            page = paginator.Paginator(object_list, self.page_size).page(
                self.request.GET.get(self.param, 1)
            )

        except paginator.InvalidPage:
            raise Http404()

        template_name = (
            pagination_template_name
            if self.request.htmx and self.request.htmx.target == self.target
            else template_name
        )

        return render(
            self.request,
            template_name,
            {
                "page_obj": page,
                "pagination_target": self.target,
                "pagination_template": pagination_template_name,
                **(extra_context or {}),
            },
        )
