import pytest
from django.template.context import RequestContext

from radiofeed.users.templatetags.account_settings import get_settings


class MockGoogleAdapter:
    def list_providers(self, request):
        return ["Google"]


class MockEmptyAdapter:
    def list_providers(self, request):
        return []


class TestGetSettings:
    @pytest.mark.django_db
    def test_get_settings(self, rf, mocker, user):
        mocker.patch(
            "radiofeed.users.templatetags.account_settings.get_adapter",
            return_value=MockEmptyAdapter(),
        )

        req = rf.get("/")
        req.user = user
        context = get_settings(RequestContext(req), "preferences")
        assert context["current_item"]["label"] == "Preferences"
        assert len(context["items"]) == 5

    @pytest.mark.django_db
    def test_connections(self, rf, mocker, user):
        mocker.patch(
            "radiofeed.users.templatetags.account_settings.get_adapter",
            return_value=MockGoogleAdapter(),
        )
        req = rf.get("/")
        req.user = user
        context = get_settings(RequestContext(req), "social_logins")
        assert context["current_item"]["label"] == "Social Logins"
        assert len(context["items"]) == 6

    @pytest.mark.django_db
    def test_invalid_item(self, rf, user):
        req = rf.get("/")
        req.user = user
        with pytest.raises(KeyError):
            get_settings(RequestContext(req), "not_found")
