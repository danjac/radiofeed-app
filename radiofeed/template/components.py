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
