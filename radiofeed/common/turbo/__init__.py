# Django
from django.template.loader import render_to_string


def render_turbo_stream(action, target, content=""):
    return f'<turbo-stream target="{target}" action="{action}"><template>{content}</template></turbo-stream>'


def render_turbo_stream_template_to_string(template, context, action, target, **kwargs):
    return render_turbo_stream(
        action, target, render_to_string(template, context, **kwargs)
    )
