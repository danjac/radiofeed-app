# Django
from django import template

# Local
from . import paginate as _paginate

register = template.Library()


@register.simple_tag(takes_context=True)
def paginate(context, object_list, **pagination_kwargs):
    """Creates paginated object"""
    return _paginate(context["request"], object_list, **pagination_kwargs)


@register.simple_tag(takes_context=True)
def pagination_url(context, page_number, param="page"):
    """
    Inserts the "page" query string parameter with the
    provided page number into the template, preserving the original
    request path and any other query string parameters.

    Given the above and a URL of "/search?q=test" the result would
    be something like:

    "/search?q=test&page=3"
    """
    request = context["request"]
    params = request.GET.copy()
    params[param] = page_number
    return request.path + "?" + params.urlencode()
