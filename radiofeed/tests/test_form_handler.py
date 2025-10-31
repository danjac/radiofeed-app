from django.forms import CharField, Form

from radiofeed.form_handler import handle_form


class TestFormHandler:
    class MyForm(Form):
        name = CharField(required=True)

    def test_not_submitted(self, rf):
        req = rf.get("/some-path")
        result = handle_form(self.MyForm, req)
        assert not result
        assert result.is_submitted is False
        assert result.is_valid is False

    def test_submitted_invalid(self, rf):
        req = rf.post("/some-path", data={})
        result = handle_form(self.MyForm, req)
        assert not result
        assert result.is_submitted is True
        assert result.is_valid is False

    def test_submitted_valid(self, rf):
        req = rf.post("/some-path", data={"name": "Test User"})
        result = handle_form(self.MyForm, req)
        assert result
        assert result.is_submitted is True
        assert result.is_valid is True
