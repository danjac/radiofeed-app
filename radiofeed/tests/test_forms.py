import http

from django import forms

from radiofeed.forms import handle_form


class MyForm(forms.Form):
    name = forms.CharField(required=True, min_length=1)


class TestHandleForm:
    def test_get(self, rf):
        req = rf.get("/")
        result = handle_form(MyForm, req)
        assert not result
        assert isinstance(result.form, MyForm)
        assert result.status == http.HTTPStatus.OK

    def test_post_ok(self, rf):
        req = rf.post("/", {"name": "test"})
        result = handle_form(MyForm, req)
        assert result
        assert isinstance(result.form, MyForm)
        assert result.status == http.HTTPStatus.OK

    def test_post_invalid(self, rf):
        req = rf.post("/")
        result = handle_form(MyForm, req)
        assert not result
        assert isinstance(result.form, MyForm)
        assert result.status == http.HTTPStatus.UNPROCESSABLE_ENTITY
