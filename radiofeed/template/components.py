from typing import Dict

from django.forms import Form as DjangoForm

from django_components import component

from .defaulttags import htmlattrs


class Form(component.Component):
    def context(
        self, form: DjangoForm, action_url: str = "", css_class: str = "", **attrs
    ) -> Dict:
        return {
            "form": form,
            "action_url": action_url,
            "css_class": css_class,
            "attrs": htmlattrs(attrs),
        }

    def template(self, context: Dict) -> str:
        # tmp name for now: move to _form.html later
        return "forms/_form_component.html"


component.registry.register(name="form", component=Form)


class Button(component.Component):
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


component.registry.register(name="button", component=Button)


class Svg(component.Component):
    def context(self, name: str, css_class="", **attrs) -> Dict:
        return {
            "name": name,
            "css_class": css_class,
            "attrs": htmlattrs(attrs),
        }

    def template(self, context: Dict) -> str:
        return f"svg/_{context['name']}.svg"


component.registry.register(name="svg", component=Svg)
