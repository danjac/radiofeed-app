from typing import Dict

from django.forms import Form

from django_components import component

from .defaulttags import htmlattrs


class FormComponent(component.Component):
    def context(
        self, form: Form, action_url: str = "", css_class: str = "", **attrs
    ) -> Dict:
        return {
            "form": form,
            "action_url": action_url,
            "css_class": css_class,
            "attrs": htmlattrs(attrs),
        }

    def template(self, context: Dict) -> str:
        return "forms/_form.html"


component.registry.register(name="form", component=FormComponent)


class ButtonComponent(component.Component):
    def context(
        self,
        text: str,
        icon: str = "",
        type: str = "default",
        css_class: str = "",
        **attrs,
    ) -> Dict:
        return {
            "text": text,
            "icon": icon,
            "type": type,
            "css_class": css_class,
            "attrs": htmlattrs(attrs),
        }

    def template(self, context: Dict) -> str:
        return "forms/_button.html"


component.registry.register(name="button", component=ButtonComponent)


class SvgComponent(component.Component):
    def context(self, name: str, css_class="", **attrs) -> Dict:
        return {
            "name": name,
            "css_class": css_class,
            "attrs": htmlattrs(attrs),
        }

    def template(self, context: Dict) -> str:
        return f"svg/_{context['name']}.svg"


component.registry.register(name="svg", component=SvgComponent)
