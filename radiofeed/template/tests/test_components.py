from django import forms

from ..components import ButtonComponent, FormComponent, ShareButtonsComponent


class MyForm(forms.Form):
    text = forms.CharField()


class TestFormComponent:
    def test_context(self):
        form = MyForm()
        ctx = FormComponent("form").context(form)
        assert ctx["form"] == form


class TestButtonComponent:
    def test_context_is_button(self):
        ctx = ButtonComponent("button").context("test")
        assert ctx["tag"] == "button"

    def test_context_is_link(self):
        ctx = ButtonComponent("button").context("test", href="/")
        assert ctx["tag"] == "a"


class TestShareButtonsComponent:
    def test_share(self, rf):
        url = "/podcasts/1234/test/"
        comp = ShareButtonsComponent("share_buttons")
        comp.outer_context = {"request": rf.get(url)}
        share_urls = comp.context(url, "Test Podcast")["share_urls"]

        assert (
            share_urls["email"]
            == "mailto:?subject=Test%20Podcast&body=http%3A//testserver/podcasts/1234/test/"
        )

        assert (
            share_urls["facebook"]
            == "https://www.facebook.com/sharer/sharer.php?u=http%3A//testserver/podcasts/1234/test/"
        )

        assert (
            share_urls["twitter"]
            == "https://twitter.com/share?url=http%3A//testserver/podcasts/1234/test/&text=Test%20Podcast"
        )

        assert (
            share_urls["linkedin"]
            == "https://www.linkedin.com/sharing/share-offsite/?url=http%3A//testserver/podcasts/1234/test/"
        )
