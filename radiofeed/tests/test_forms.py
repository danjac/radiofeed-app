from django import forms
from django.core import validators

from radiofeed.forms import handle_form


class TestHandleForm:
    class MyForm(forms.Form):
        value = forms.CharField(
            required=True,
            validators=[validators.MinLengthValidator(5)],
        )

    def test_get(self, rf):
        result = handle_form(rf.get("/"), self.MyForm)
        assert not result
        assert result.processed is False
        assert result.success is False

    def test_post_invalid(self, rf):
        result = handle_form(rf.post("/", {"value": "ok"}), self.MyForm)
        assert not result
        assert result.processed is True
        assert result.success is False

    def test_post_valid(self, rf):
        result = handle_form(
            rf.post("/", {"value": "should be long enough"}), self.MyForm
        )
        assert result
        assert result.processed is True
        assert result.success is True
