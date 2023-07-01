from django import forms

from radiofeed.forms import handle_form


class MyForm(forms.Form):
    name = forms.CharField(required=True)


class TestHandleForm:
    def test_get(self, rf):
        form, success = handle_form(MyForm, rf.get("/"))

        assert not success
        assert not form.errors

    def test_post_ok(self, rf):
        form, success = handle_form(MyForm, rf.post("/", {"name": "testing"}))

        assert success
        assert not form.errors

    def test_post_errors(self, rf):
        form, success = handle_form(MyForm, rf.post("/"))

        assert not success
        assert form.errors
