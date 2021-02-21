from django import forms

from ..components import ButtonComponent, FormComponent


class MyForm(forms.Form):
    text = forms.CharField()


class TestFormComponent:
    def test_context(self):
        form = MyForm()
        ctx = FormComponent("form").context(form)
        assert ctx["form"] == form


class TestButtonComponent:
    def test_context_is_button(self):
        ctx = ButtonComponent("button").context("test")
        assert ctx["tag"] == "button"

    def test_context_is_link(self):
        ctx = ButtonComponent("button").context("test", href="/")
        assert ctx["tag"] == "a"
