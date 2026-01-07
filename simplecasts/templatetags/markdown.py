from django import template

from simplecasts.services import sanitizer

register = template.Library()


@register.inclusion_tag("markdown.html")
def markdown(text: str) -> dict:
    """Render content as Markdown."""
    return {"markdown": sanitizer.markdown(text)}
