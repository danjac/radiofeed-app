import pytest
from django.template.context import RequestContext

from radiofeed.users.templatetags.users import get_account_settings


class MockGoogleAdapter:
    def list_providers(self, _):
        return ["Google"]


class MockEmptyAdapter:
    def list_providers(self, _):
        return []


class TestGetAccountSettings:
    @pytest.mark.django_db
    def test_get_account_settings(self, rf, mocker, user):
        mocker.patch(
            "radiofeed.users.templatetags.users.get_adapter",
            return_value=MockEmptyAdapter(),
        )

        req = rf.get("/")
        req.user = user
        settings = get_account_settings(RequestContext(req), "preferences")
        assert settings["active"]["label"] == "Preferences"
        assert len(settings["items"]) == 6

    @pytest.mark.django_db
    def test_connections(self, rf, mocker, user):
        mocker.patch(
            "radiofeed.users.templatetags.users.get_adapter",
            return_value=MockGoogleAdapter(),
        )
        req = rf.get("/")
        req.user = user
        settings = get_account_settings(RequestContext(req), "social_logins")
        assert settings["active"]["label"] == "Social Logins"
        assert len(settings["items"]) == 7

    @pytest.mark.django_db
    def test_invalid_item(self, rf, user):
        req = rf.get("/")
        req.user = user
        settings = get_account_settings(RequestContext(req), "not_found")
        assert settings["active"]["label"] == "Preferences"
