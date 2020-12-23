# Django
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.tag
def turbostream(parser, token):
    nodelist = parser.parse(("endturbostream"))
    parser.delete_first_token()
    return TurboStreamNode(nodelist)


class TurboStreamNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):

        is_turbo_stream = context.get("_is_turbo_stream", False)
        action = context.get("_turbo_stream_action", None)
        target = context.get("_turbo_stream_target", None)

        output = self.nodelist.render(context)
        if is_turbo_stream and action and target:
            start_tag = mark_safe(
                f'<turbo-stream action="{action}" target="{target}"><template>'
            )
            end_tag = mark_safe("</template></turbo-stream>")

            return start_tag + output + end_tag
        else:
            return output
