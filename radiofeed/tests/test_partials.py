import pytest
from django_htmx.middleware import HtmxDetails

from radiofeed.partials import render_partial_for_target


class TestRenderPartialForTarget:
    @pytest.fixture
    def mock_render(self, mocker):
        return mocker.patch("radiofeed.partials.render")

    def test_target_matches(self, rf, mock_render):
        request = rf.get("/", HTTP_HX_TARGET="target", HTTP_HX_REQUEST="true")
        request.htmx = HtmxDetails(request)

        render_partial_for_target(
            request,
            "template.html",
            target="target",
            partial="partial",
        )
        mock_render.assert_called_once_with(request, "template.html#partial", None)

    def test_target_not_matches(self, rf, mock_render):
        request = rf.get("/", HTTP_HX_TARGET="other", HTTP_HX_REQUEST="true")
        request.htmx = HtmxDetails(request)

        render_partial_for_target(
            request,
            "template.html",
            target="target",
            partial="partial",
        )
        mock_render.assert_called_once_with(request, "template.html", None)

    def test_target_not_htmx(self, rf, mock_render):
        request = rf.get("/")
        request.htmx = HtmxDetails(request)

        render_partial_for_target(
            request,
            "template.html",
            target="target",
            partial="partial",
        )
        mock_render.assert_called_once_with(request, "template.html", None)
