from django.http import HttpRequest
from django.template.response import TemplateResponse


class HtmxTemplateResponse(TemplateResponse):
    """Conditionally render a template partial on HTMX request.

    If `partial` is provided, and HX-Request in header, will render the template partial, otherwise will render the entire template.

    If `target` is provided, will also try to match the `HX-Target` header.
    """

    def __init__(
        self,
        request: HttpRequest,
        template_name: str,
        context: dict | None = None,
        *,
        partial: str | None = None,
        target: str | None = None,
        **kwargs,
    ) -> None:
        if (
            partial
            and request.htmx
            and (target is None or target == request.htmx.target)
        ):
            template_name = f"{template_name}#{partial}"

        super().__init__(request, template_name, context, **kwargs)
