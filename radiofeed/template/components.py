from typing import Dict

from django.forms import Form

from django_components import component

from .defaulttags import htmlattrs


class FormComponent(component.Component):
    def context(self, form: Form, action_url: str = "", **attrs) -> Dict:
        return {"form": form, "action_url": action_url, "attrs": htmlattrs(attrs)}

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
            "tag": "a" if "href" in attrs else "button",
            "attrs": htmlattrs(attrs),
        }

    def template(self, context: Dict) -> str:
        return "forms/_button.html"


component.registry.register(name="button", component=ButtonComponent)


class IconComponent(component.Component):
    ...
