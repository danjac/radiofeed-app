import pytest
from allauth.socialaccount.models import SocialApp
from django.template.loader import get_template

from radiofeed.users.tests.factories import create_email_address


@pytest.fixture()
def player(mocker):
    player = mocker.Mock()
    player.get.return_value = None
    return player


@pytest.fixture()
def req(rf, anonymous_user, player, site):
    req = rf.get("/")
    req.player = player
    req.user = anonymous_user
    req.htmx = False
    req.site = site
    return req


@pytest.fixture()
def auth_req(req, user, player):
    req.user = user

    req.player = player

    return req


@pytest.fixture()
def social_app(site):
    app = SocialApp.objects.create(provider="google", name="Google")
    app.sites.add(site)
    return app


class TestSocialAccount:
    """Test overridden allauth account templates."""

    @pytest.mark.django_db()
    def test_signup(self, req, mocker, site):
        assert get_template("socialaccount/signup.html").render(
            {
                "redirect_field_name": "redirect",
                "redirect_field_value": "/",
                "site": site,
                "account": mocker.Mock(),
                "form": mocker.Mock(),
            },
            request=req,
        )

    @pytest.mark.django_db()
    def test_login(self, req, site, mocker):
        assert get_template("socialaccount/login.html").render(
            {
                "redirect_field_name": "redirect",
                "redirect_field_value": "/",
                "site": site,
                "account": mocker.Mock(),
                "form": mocker.Mock(),
                "provider": mocker.Mock(),
            },
            request=req,
        )

    @pytest.mark.django_db()
    def test_authentication_error(self, req, mocker):
        assert get_template("socialaccount/authentication_error.html").render(
            {"auth_error": mocker.Mock()},
            request=req,
        )

    @pytest.mark.django_db()
    def test_login_connect(self, req, mocker):
        assert get_template("socialaccount/login.html").render(
            {
                "process": "connect",
                "provider": mocker.Mock(),
            },
            request=req,
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

    @pytest.mark.django_db()
    def test_email_verification_required(self, req):
        assert get_template("account/verified_email_required.html").render(
            {}, request=req
        )

    @pytest.mark.django_db()
    def test_verification_sent(self, req):
        assert get_template("account/verification_sent.html").render({}, request=req)

    @pytest.mark.django_db()
    def test_email(self, auth_req, mocker):
        create_email_address(user=auth_req.user, primary=True)
        create_email_address(user=auth_req.user, primary=False)
        create_email_address(user=auth_req.user, primary=False, verified=False)

        assert get_template("account/email.html").render(
            {
                "user": auth_req.user,
                "can_add_email": True,
                "form": mocker.Mock(),
            },
            request=auth_req,
        )

    @pytest.mark.django_db()
    def test_email_no_emails(self, auth_req, mocker):
        assert get_template("account/email.html").render(
            {
                "user": auth_req.user,
                "can_add_email": True,
                "form": mocker.Mock(),
            },
            request=auth_req,
        )

    @pytest.mark.django_db()
    def test_email_confirm(self, req, mocker):
        confirmation = mocker.Mock()
        confirmation.key = "test"
        assert get_template("account/email_confirm.html").render(
            {
                "confirmation": confirmation,
                "form": mocker.Mock(),
            },
            request=req,
        )

    @pytest.mark.django_db()
    def test_email_confirm_no_confirmation(self, req, mocker):
        assert get_template("account/email_confirm.html").render(
            {
                "confirmation": None,
                "form": mocker.Mock(),
            },
            request=req,
        )

    @pytest.mark.django_db()
    def test_account_inactive(self, req):
        assert get_template("account/account_inactive.html").render({}, request=req)

    @pytest.mark.django_db()
    def test_password_change(self, auth_req, mocker):
        assert get_template("account/password_change.html").render(
            {
                "form": mocker.Mock(),
            },
            request=auth_req,
        )

    @pytest.mark.django_db()
    def test_password_reset(self, auth_req, mocker):
        assert get_template("account/password_reset.html").render(
            {
                "form": mocker.Mock(),
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

    @pytest.mark.django_db()
    def test_password_reset_from_key(self, req, mocker):
        form = mocker.Mock()

        assert get_template("account/password_reset_from_key.html").render(
            {"form": form}, request=req
        )

    @pytest.mark.django_db()
    def test_password_reset_from_key_token_fail(self, req, mocker):
        form = mocker.Mock()

        assert get_template("account/password_reset_from_key.html").render(
            {"form": form, "token_fail": True}, request=req
        )

    @pytest.mark.django_db()
    def test_password_reset_from_key_no_form(self, req, mocker):
        assert get_template("account/password_reset_from_key.html").render(
            {}, request=req
        )

    @pytest.mark.django_db()
    def test_password_reset_from_key_done(self, req):
        assert get_template("account/password_reset_from_key_done.html").render(
            {}, request=req
        )

    @pytest.mark.django_db()
    def test_password_set(self, req, mocker):
        assert get_template("account/password_set.html").render(
            {
                "form": mocker.Mock(),
            },
            request=req,
        )

    @pytest.mark.django_db()
    def test_login(self, req, social_app, mocker):
        assert get_template("account/login.html").render(
            {
                "redirect_field_name": "redirect",
                "redirect_field_value": "/",
                "signup_url": "/signup/",
                "auth_params": {},
                "form": mocker.Mock(),
                "scope": mocker.Mock(),
            },
            request=req,
        )

    @pytest.mark.django_db()
    def test_signup(self, req, social_app, mocker, site):
        assert get_template("account/signup.html").render(
            {
                "redirect_field_name": "redirect",
                "redirect_field_value": "/",
                "login_url": "/login/",
                "auth_params": {},
                "site": site,
                "form": mocker.Mock(),
                "scope": mocker.Mock(),
            },
            request=req,
        )
