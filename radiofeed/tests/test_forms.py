import http

from django import forms

from radiofeed.forms import handle_form


class MyForm(forms.Form):
    name = forms.CharField(required=True)


class TestHandleForm:
    def test_get(self, rf):
        form, result = handle_form(MyForm, rf.get("/"))

        assert not result
        assert not form.errors
        assert result.status == http.HTTPStatus.OK

    def test_post_ok(self, rf):
        form, result = handle_form(MyForm, rf.post("/", {"name": "testing"}))

        assert result
        assert not form.errors
        assert result.status == http.HTTPStatus.OK

    def test_post_errors(self, rf):
        form, result = handle_form(MyForm, rf.post("/"))

        assert not result
        assert form.errors
        assert result.status == http.HTTPStatus.UNPROCESSABLE_ENTITY
