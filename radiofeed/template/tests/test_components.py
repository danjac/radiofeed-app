from django import forms

from ..components import FormComponent


class MyForm(forms.Form):
    text = forms.CharField()


class TestFormComponents:
    def test_context(self):
        form = MyForm()
        ctx = FormComponent("form").context(form)
        assert ctx["form"] == form
