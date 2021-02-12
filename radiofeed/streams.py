import dataclasses
import functools

from django.conf import settings
from django.contrib import messages

from turbo_response import TurboStream


@dataclasses.dataclass
class Message:
    message: str
    tags: str

    def __str__(self):
        return self.message


def render_close_modal() -> str:
    return TurboStream("modal").update.render()


def render_message(message: str, level: int):
    return (
        TurboStream("messages")
        .append.template(
            "_message.html",
            {"message": Message(message, tags=settings.MESSAGE_TAGS[level])},
        )
        .render()
    )


render_success_message = functools.partial(render_message, level=messages.SUCCESS)
render_info_message = functools.partial(render_message, level=messages.INFO)
