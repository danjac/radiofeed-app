from django import forms
from django.core import validators

from radiofeed.form_handler import handle_form


class MyForm(forms.Form):
    value = forms.CharField(validators=[validators.MinLengthValidator(3)])

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)


class TestHandleForm:
    def test_get(self, rf):
        req = rf.get("/")
        result = handle_form(req, MyForm)
        assert not result
        assert result.form
        assert result.processed is False
        assert result.success is False

    def test_get_with_kwargs(self, rf):
        req = rf.get("/")
        result = handle_form(req, MyForm, instance="something")
        assert not result
        assert result.form
        assert result.form.instance == "something"
        assert result.processed is False
        assert result.success is False

    def test_post_invalid(self, rf):
        req = rf.post("/", {"value": "a"})
        result = handle_form(req, MyForm)
        assert not result
        assert result.form
        assert result.processed is True
        assert result.success is False

    def test_post_valid(self, rf):
        req = rf.post("/", {"value": "abc"})
        result = handle_form(req, MyForm)
        assert result
        assert result.form
        assert result.processed is True
        assert result.success is True

    def test_post_valid_with_kwargs(self, rf):
        req = rf.post("/", {"value": "abc"})
        result = handle_form(req, MyForm, instance="something")
        assert result
        assert result.form
        assert result.form.instance == "something"
        assert result.processed is True
        assert result.success is True
