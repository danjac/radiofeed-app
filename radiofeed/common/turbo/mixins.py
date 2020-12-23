# Django
from django.core.exceptions import ImproperlyConfigured

# Local
from .response import TurboStreamResponse


class TurboStreamFormMixin:
    turbo_stream_action = None
    turbo_stream_target = None
    turbo_stream_template = None

    def get_turbo_stream_action(self):
        return self.turbo_stream_action

    def get_turbo_stream_target(self):
        return self.turbo_stream_target

    def get_turbo_stream_template(self):
        return self.turbo_stream_template

    def form_invalid(self, form):
        template = self.get_turbo_stream_template()
        action = self.get_turbo_stream_action()
        target = self.get_turbo_stream_target()

        if template is None:
            raise ImproperlyConfigured("turbo_stream_template must be set")

        if action is None:
            raise ImproperlyConfigured("turbo_stream_action must be set")

        if target is None:
            raise ImproperlyConfigured("turbo_stream_target must be set")

        return TurboStreamResponse(
            request=self.request,
            template=self.get_turbo_stream_template(),
            target=self.get_turbo_stream_target(),
            action=self.get_turbo_stream_action(),
            context=self.get_context_data(form=form),
            using=self.template_engine,
        )
