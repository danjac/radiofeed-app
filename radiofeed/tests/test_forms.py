import http

from django import forms

from radiofeed.forms import handle_form


class MyForm(forms.Form):
    name = forms.CharField(required=True)


class TestHandleForm:
    def test_get(self, rf):
        form, result = handle_form(MyForm, rf.get("/"))

        assert not result
        assert not result.is_bound
        assert not result.is_valid
        assert result.status == http.HTTPStatus.OK

        assert not form.errors

    def test_post_ok(self, rf):
        form, result = handle_form(MyForm, rf.post("/", {"name": "testing"}))

        assert result
        assert result.is_bound
        assert result.is_valid
        assert result.status == http.HTTPStatus.OK

        assert not form.errors

    def test_post_errors(self, rf):
        form, result = handle_form(MyForm, rf.post("/"))

        assert not result
        assert result.is_bound
        assert not result.is_valid
        assert result.status == http.HTTPStatus.UNPROCESSABLE_ENTITY

        assert form.errors
