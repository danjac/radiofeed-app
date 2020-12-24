# Django
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe


class TurboStreamRemoveResponse(HttpResponse):
    """Sends an empty 'remove' stream"""

    def __init__(self, target, **kwargs):
        super().__init__(
            f'<turbo-stream target="{target}" action="remove"></turbo-stream>',
            content_type="text/html; turbo-stream;",
        )


class TurboStreamTemplateResponse(TemplateResponse):
    def __init__(self, request, template, context, action, target, **kwargs):

        super().__init__(
            request,
            template,
            context,
            content_type="text/html; turbo-stream;",
            **kwargs,
        )

        self._target = target
        self._action = action

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
            f'<turbo-stream action="{self._action}" target="{self._target}"><template>'
        )
        end_tag = mark_safe("</template></turbo-stream>")
        return start_tag + content + end_tag


class TurboFrameTemplateResponse(TemplateResponse):
    def __init__(self, request, template, context, dom_id, **kwargs):

        super().__init__(
            request, template, context, **kwargs,
        )

        self._dom_id = dom_id
        self.context_data.update({"turbo_frame_dom_id": dom_id, "is_turbo_frame": True})

    @property
    def rendered_content(self):
        content = super().rendered_content
        start_tag = mark_safe(f'<turbo-frame id="{self._dom_id}">')
        end_tag = mark_safe("</turbo-frame>")
        return start_tag + content + end_tag
