from __future__ import annotations

import enum
import json

from django.http import HttpResponse


class HxTrigger(enum.Enum):
    HX_TRIGGER = "HX-Trigger"
    HX_TRIGGER_AFTER_SETTLE = "HX-Trigger-After-Settle"
    HX_TRIGGER_AFTER_SWAP = "HX-Trigger-After-Swap"


def with_hx_trigger(
    response: HttpResponse,
    data: str | dict,
    header: HxTrigger = HxTrigger.HX_TRIGGER,
) -> HttpResponse:
    """Returns HX-Trigger header. If header already
    added to response, will add the new trigger
    to the existing header.

    See:

    https://htmx.org/headers/hx-trigger/
    """

    if not data:
        return response

    if trigger := response.headers.get(header.value, None):
        try:
            payload = json.loads(trigger)
        except json.JSONDecodeError:
            # probably plain string
            payload = {trigger: ""}
    else:
        payload = {}

    if isinstance(data, str):
        data = {data: ""}

    response[header.value] = json.dumps({**payload, **data})
    return response
