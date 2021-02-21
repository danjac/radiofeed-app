from typing import Dict
from urllib import parse

from django.forms import Field, Form

from django_components import component


class FormComponent(component.Component):
    def context(self, form: Form, action_url: str = "", **attrs) -> Dict:
        return {
            "form": form,
            "action_url": action_url,
            "attrs": attrs,
        }

    def template(self, context: Dict) -> str:
        return "components/forms/_form.html"


component.registry.register(name="form", component=FormComponent)


class FormFieldComponent(component.Component):
    def context(self, field: Field, css_class: str = "") -> Dict:
        return {"field": field, "css_class": css_class}

    def template(self, context: Dict) -> str:
        input_type = context["field"].field.widget.input_type
        return (
            "components/forms/_checkbox_field.html"
            if input_type == "checkbox"
            else "components/forms/_field.html"
        )


component.registry.register(name="form_field", component=FormFieldComponent)


class SearchFormComponent(component.Component):
    def context(
        self,
        search_url: str = "",
        search_param: str = "q",
        placeholder: str = "",
        css_class: str = "",
        **attrs,
    ):
        return {
            "search_url": search_url,
            "search_param": search_param,
            "placeholder": placeholder,
            "css_class": css_class,
            "attrs": attrs,
        }

    def template(self, context: Dict) -> str:
        return "components/forms/_search_form.html"


component.registry.register(name="search_form", component=SearchFormComponent)


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
            "attrs": attrs,
        }

    def template(self, context: Dict) -> str:
        return "components/buttons/_button.html"


component.registry.register(name="button", component=ButtonComponent)


class RemoveButtonComponent(component.Component):
    def context(self, remove_url: str, css_class: str = "", title: str = "") -> Dict:
        return {
            "remove_url": remove_url,
            "css_class": css_class,
            "title": title,
        }

    def template(self, context: Dict) -> str:
        return "components/buttons/_remove_button.html"


component.registry.register(name="remove_button", component=RemoveButtonComponent)


class IconComponent(component.Component):
    def context(self, name: str, css_class: str = "", title: str = "", **attrs) -> Dict:
        return {
            "name": name,
            "css_class": css_class,
            "title": title,
            "attrs": attrs,
        }

    def template(self, context: Dict) -> str:
        return f"components/icons/_{context['name']}.svg"


component.registry.register(name="icon", component=IconComponent)


class ShareButtonsComponent(component.Component):
    def context(self, url: str, subject: str, css_class: str = "") -> Dict:
        url = parse.quote(self.outer_context["request"].build_absolute_uri(url))
        subject = parse.quote(subject)

        return {
            "css_class": css_class,
            "share_urls": {
                "email": f"mailto:?subject={subject}&body={url}",
                "facebook": f"https://www.facebook.com/sharer/sharer.php?u={url}",
                "twitter": f"https://twitter.com/share?url={url}&text={subject}",
                "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={url}",
            },
        }

    def template(self, context: Dict) -> str:
        return "components/buttons/_share_buttons.html"


component.registry.register(name="share_buttons", component=ShareButtonsComponent)
