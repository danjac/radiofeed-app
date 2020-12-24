# All auth views

# Third Party Libraries
from allauth.account import views as account_views

# RadioFeed
from radiofeed.common.turbo.mixins import TurboStreamFormMixin


class LoginView(TurboStreamFormMixin, account_views.LoginView):
    turbo_stream_target = "login-form"
    turbo_stream_template = "account/_login.html"


login = LoginView.as_view()


class SignupView(TurboStreamFormMixin, account_views.SignupView):
    turbo_stream_target = "signup-form"
    turbo_stream_template = "account/_signup.html"


signup = SignupView.as_view()


class EmailView(TurboStreamFormMixin, account_views.EmailView):
    turbo_stream_target = "add-email-form"
    turbo_stream_template = "account/_add_email.html"


email = EmailView.as_view()


class PasswordChangeView(TurboStreamFormMixin, account_views.PasswordChangeView):
    turbo_stream_target = "password-change-form"
    turbo_stream_template = "account/_password_change.html"


password_change = PasswordChangeView.as_view()


class PasswordSetView(TurboStreamFormMixin, account_views.PasswordSetView):
    turbo_stream_target = "password-set-form"
    turbo_stream_template = "account/_password_set.html"


password_set = PasswordSetView.as_view()


class PasswordResetView(TurboStreamFormMixin, account_views.PasswordResetView):
    turbo_stream_target = "password-reset-form"
    turbo_stream_template = "account/_password_reset.html"


password_reset = PasswordResetView.as_view()


class PasswordResetFromKeyView(
    TurboStreamFormMixin, account_views.PasswordResetFromKeyView
):
    turbo_stream_target = "password-reset-from-key-form"
    turbo_stream_template = "account/_password_reset_from_key.html"


password_reset_from_key = PasswordResetFromKeyView.as_view()
