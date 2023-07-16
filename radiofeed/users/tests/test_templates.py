import pytest
from django.template.loader import get_template

from radiofeed.users.tests.factories import create_email_address


@pytest.fixture()
def player(mocker):
    player = mocker.Mock()
    player.get.return_value = None
    return player


@pytest.fixture()
def req(rf, anonymous_user, player):
    req = rf.get("/")
    req.player = player
    req.user = anonymous_user
    return req


@pytest.fixture()
def auth_req(req, user, player):
    req.user = user

    req.player = player

    return req


class TestSocialAccount:
    """Test overridden allauth account templates."""

    def test_signup(self, req):
        assert get_template("socialaccount/signup.html").render(
            {"redirect_field_value": "/"}, request=req
        )

    def test_login(self, req):
        assert get_template("socialaccount/login.html").render(
            {"redirect_field_value": "/"}, request=req
        )

    def test_authentication_error(self, req):
        assert get_template("socialaccount/authentication_error.html").render(
            {}, request=req
        )

    def test_login_connect(self, req):
        assert get_template("socialaccount/login.html").render(
            {"process": "connect"}, request=req
        )

    @pytest.mark.django_db()
    def test_connections(self, auth_req, mocker):
        form = mocker.Mock()
        form.accounts = [mocker.Mock()]
        assert get_template("socialaccount/connections.html").render(
            {"form": form}, request=auth_req
        )

    @pytest.mark.django_db()
    def test_connections_no_accounts(self, auth_req, mocker):
        form = mocker.Mock()
        form.accounts = []
        assert get_template("socialaccount/connections.html").render(
            {"form": form}, request=auth_req
        )


class TestAccount:
    """Test overridden allauth account templates."""

    def test_email_verification_required(self, req):
        assert get_template("account/verified_email_required.html").render(
            {}, request=req
        )

    def test_verification_sent(self, req):
        assert get_template("account/verification_sent.html").render({}, request=req)

    @pytest.mark.django_db()
    def test_email(self, auth_req):
        create_email_address(user=auth_req.user, primary=True)
        create_email_address(user=auth_req.user, primary=False)

        assert get_template("account/email.html").render(
            {
                "user": auth_req.user,
                "can_add_email": True,
            },
            request=auth_req,
        )

    @pytest.mark.django_db()
    def test_email_no_emails(self, auth_req):
        assert get_template("account/email.html").render(
            {
                "user": auth_req.user,
                "can_add_email": True,
            },
            request=auth_req,
        )

    def test_email_confirm(self, req, mocker):
        confirmation = mocker.Mock()
        confirmation.key = "test"
        assert get_template("account/email_confirm.html").render(
            {
                "confirmation": confirmation,
            },
            request=req,
        )

    def test_email_confirm_no_confirmation(self, req):
        assert get_template("account/email_confirm.html").render(
            {
                "confirmation": None,
            },
            request=req,
        )

    def test_account_inactive(self, req):
        assert get_template("account/account_inactive.html").render({}, request=req)

    @pytest.mark.django_db()
    def test_password_change(self, auth_req):
        assert get_template("account/password_change.html").render({}, request=auth_req)

    @pytest.mark.django_db()
    def test_password_reset(self, auth_req):
        assert get_template("account/password_reset.html").render(
            {
                "user": auth_req.user,
            },
            request=auth_req,
        )

    @pytest.mark.django_db()
    def test_password_reset_done(self, auth_req):
        assert get_template("account/password_reset_done.html").render(
            {
                "user": auth_req.user,
            },
            request=auth_req,
        )

    def test_password_reset_from_key(self, req, mocker):
        form = mocker.Mock()

        assert get_template("account/password_reset_from_key.html").render(
            {"form": form}, request=req
        )

    def test_password_reset_from_key_token_fail(self, req, mocker):
        form = mocker.Mock()

        assert get_template("account/password_reset_from_key.html").render(
            {"form": form, "token_fail": True}, request=req
        )

    def test_password_reset_from_key_no_form(self, req, mocker):
        assert get_template("account/password_reset_from_key.html").render(
            {}, request=req
        )

    def test_password_reset_from_key_done(self, req):
        assert get_template("account/password_reset_from_key_done.html").render(
            {}, request=req
        )

    def test_password_set(self, req):
        assert get_template("account/password_set.html").render({}, request=req)

    def test_login(self, req):
        assert get_template("account/login.html").render(
            {"redirect_field_value": "/"}, request=req
        )

    def test_signup(self, req):
        assert get_template("account/signup.html").render(
            {"redirect_field_value": "/"}, request=req
        )
