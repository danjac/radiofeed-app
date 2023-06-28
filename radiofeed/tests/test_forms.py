from django import forms

from radiofeed.forms import process_form


class MyForm(forms.Form):
    name = forms.CharField(required=True, min_length=1)


class TestProcessForm:
    def test_get(self, rf):
        req = rf.get("/")
        form, success = process_form(MyForm, req)
        assert isinstance(form, MyForm)
        assert success is False
        assert not form.errors

    def test_post_ok(self, rf):
        req = rf.post("/", {"name": "test"})
        form, success = process_form(MyForm, req)
        assert isinstance(form, MyForm)
        assert success is True
        assert not form.errors

    def test_post_invalid(self, rf):
        req = rf.post("/")
        form, success = process_form(MyForm, req)
        assert isinstance(form, MyForm)
        assert success is False
        assert form.errors
