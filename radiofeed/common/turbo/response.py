# Django
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe


class TurboStreamTemplateResponse(TemplateResponse):
    def __init__(self, request, template, context, action, target, **kwargs):

        super().__init__(
            request,
            template,
            context,
            content_type="text/html; turbo-stream;",
            **kwargs,
        )

        self.turbo_stream_target = target
        self.turbo_stream_action = action

        self.context_data.update(
            {
                "turbo_stream_target": target,
                "turbo_stream_action": action,
                "is_turbo_stream": True,
            }
        )

    @property
    def rendered_content(self):
        content = super().rendered_content
        start_tag = mark_safe(
            f'<turbo-stream action="{self.turbo_stream_action}" target="{self.turbo_stream_target}"><template>'
        )
        end_tag = mark_safe("</template></turbo-stream>")
        content = start_tag + content + end_tag
        return content
