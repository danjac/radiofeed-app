import pytest
from django.template.context import RequestContext

from listenwave.users.templatetags.users import get_account_settings


class MockGoogleAdapter:
    def list_providers(self, _):
        return ["Google"]


class MockEmptyAdapter:
    def list_providers(self, _):
        return []


@pytest.fixture
def google_adapter(mocker):
    return mocker.patch(
        "listenwave.users.templatetags.users.get_adapter",
        return_value=MockGoogleAdapter(),
    )


@pytest.fixture
def empty_adapter(mocker):
    return mocker.patch(
        "listenwave.users.templatetags.users.get_adapter",
        return_value=MockEmptyAdapter(),
    )


class TestGetAccountSettings:
    @pytest.mark.django_db
    def test_no_social_logins(self, rf, empty_adapter, user):
        req = rf.get("/")
        req.user = user
        settings = get_account_settings(RequestContext(req), "preferences")
        assert settings["active"]["label"] == "Preferences"
        assert len(settings["items"]) == 6

    @pytest.mark.django_db
    def test_unusable_password(self, rf, empty_adapter, user):
        user.set_unusable_password()
        req = rf.get("/")
        req.user = user
        settings = get_account_settings(RequestContext(req), "preferences")
        assert settings["active"]["label"] == "Preferences"
        assert len(settings["items"]) == 5

    @pytest.mark.django_db
    def test_connections(self, rf, google_adapter, user):
        req = rf.get("/")
        req.user = user
        settings = get_account_settings(RequestContext(req), "connections")
        assert settings["active"]["label"] == "3rd Party Accounts"
        assert len(settings["items"]) == 7

    @pytest.mark.django_db
    def test_invalid_item(self, rf, empty_adapter, user):
        req = rf.get("/")
        req.user = user
        settings = get_account_settings(RequestContext(req), "not_found")
        assert settings["active"]["label"] == "Preferences"
