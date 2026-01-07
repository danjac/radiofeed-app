from django import template
from django.template.context import Context
from django.utils.safestring import SafeString

register = template.Library()


@register.simple_block_tag(takes_context=True)
def fragment(
    context: Context,
    content: str,
    template_name: str,
    *,
    only: bool = False,
    **extra_context,
) -> SafeString:
    """Renders include in block.

    Example:

    Calling template:

    {% fragment "header.html" %}
    title goes here
    {% endfragment %}

    header.html:

    <h1>{{ content }}</h1>

    Renders:

    <h1>title goes here</h1>

    If `only` is passed it will not include outer context.
    """

    context = context.new() if only else context

    if context.template is None:
        raise template.TemplateSyntaxError(
            "Can only be used inside a template context."
        )

    tmpl = context.template.engine.get_template(template_name)

    with context.push(content=content, **extra_context):
        return tmpl.render(context)
