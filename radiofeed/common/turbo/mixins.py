# Local
from .response import TurboStreamTemplateResponse


class TurboStreamFormMixin:
    turbo_stream_action = "update"
    turbo_stream_target = None
    turbo_stream_template = None

    def get_turbo_stream_action(self):
        return self.turbo_stream_action

    def get_turbo_stream_target(self):
        return self.turbo_stream_target

    def get_turbo_stream_template(self):
        return self.turbo_stream_template

    def form_invalid(self, form):
        return TurboStreamTemplateResponse(
            request=self.request,
            template=self.get_turbo_stream_template(),
            context=self.get_context_data(form=form),
            target=self.get_turbo_stream_target(),
            action=self.get_turbo_stream_action(),
            using=self.template_engine,
        )
