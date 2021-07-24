from __future__ import annotations

import enum
import http
import json

from django.http import HttpResponse


class HttpResponseConflict(HttpResponse):
    status_code: int = http.HTTPStatus.CONFLICT


class HttpResponseNoContent(HttpResponse):
    status_code: int = http.HTTPStatus.NO_CONTENT


class HxTrigger(enum.Enum):
    HX_TRIGGER = "HX-Trigger"
    HX_TRIGGER_AFTER_SETTLE = "HX-Trigger-After-Settle"
    HX_TRIGGER_AFTER_SWAP = "HX-Trigger-After-Swap"


def with_hx_trigger(
    response: HttpResponse,
    data: str | dict,
    header: HxTrigger = HxTrigger.HX_TRIGGER,
) -> HttpResponse:

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
