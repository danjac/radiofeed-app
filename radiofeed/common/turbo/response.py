# Django
from django.template.response import TemplateResponse


class TurboStreamResponse(TemplateResponse):
    def __init__(self, request, template_name, context, *, action, target, **kwargs):

        super().__init__(
            request,
            template_name,
            context,
            content_type="text/html; turbo-stream;",
            **kwargs
        )
        self.context_data.update(
            {
                "_turbo_stream_target": target,
                "_turbo_stream_action": action,
                "_is_turbo_stream": True,
            }
        )
