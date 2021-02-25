import dataclasses

from typing import Type

from django.forms import Form
from django.http import HttpRequest
from django.template.context import RequestContext
from django_components.component import registry


def render_component(request: HttpRequest, component_name: str, *args, **kwargs) -> str:
    """Render a component as string. Use with turbo streams/frames
    to render the component in a response."""
    context = RequestContext(request)

    component = registry.get(component_name)(component_name)
    component.outer_context = context.flatten()

    with context.update(component.context(*args, **kwargs)):
        return component.render(context)


@dataclasses.dataclass
class FormResult:
    form: Form
    is_valid: bool = False

    def __bool__(self) -> bool:
        return self.is_valid


def handle_form(
    request: HttpRequest,
    form_class: Type[Form],
    use_request: bool = False,
    **form_kwargs
) -> FormResult:
    if use_request:
        form_kwargs["request"] = request

    if request.method in ("POST", "PUT"):
        form = form_class(data=request.POST, files=request.FILES, **form_kwargs)
        return FormResult(form, form.is_valid())

    return FormResult(form_class(**form_kwargs))
