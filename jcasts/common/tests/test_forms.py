import pytest

from django import forms
from django.core import validators

from jcasts.common.forms import handle_form


class TestHandleForm:
    @pytest.fixture(scope="class")
    def form_class(self):
        class MyForm(forms.Form):
            name = forms.CharField(
                required=True, validators=[validators.MinLengthValidator(3)]
            )

        return MyForm

    def test_get(self, rf, form_class):
        with handle_form(rf.get("/"), form_class, initial={"name": "test"}) as (
            form,
            success,
        ):
            assert isinstance(form, form_class)
            assert form.initial["name"] == "test"
            assert not success

    def test_post_invalid(self, rf, form_class):
        with handle_form(rf.post("/", {"name": "t"}), form_class) as (form, success):
            assert isinstance(form, form_class)
            assert not success

    def test_post_valid(self, rf, form_class):
        with handle_form(rf.post("/", {"name": "test"}), form_class) as (form, success):
            assert isinstance(form, form_class)
            assert success
