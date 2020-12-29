# All auth views

# Third Party Libraries
from allauth.account import views as account_views
from turbo_response.mixins import TurboStreamFormMixin


class LoginView(TurboStreamFormMixin, account_views.LoginView):
    turbo_stream_target = "login-form"


login = LoginView.as_view()


class SignupView(TurboStreamFormMixin, account_views.SignupView):
    turbo_stream_target = "signup-form"


signup = SignupView.as_view()


class EmailView(TurboStreamFormMixin, account_views.EmailView):
    turbo_stream_target = "add-email-form"


email = EmailView.as_view()


class PasswordChangeView(TurboStreamFormMixin, account_views.PasswordChangeView):
    turbo_stream_target = "password-change-form"


password_change = PasswordChangeView.as_view()


class PasswordSetView(TurboStreamFormMixin, account_views.PasswordSetView):
    turbo_stream_target = "password-set-form"


password_set = PasswordSetView.as_view()


class PasswordResetView(TurboStreamFormMixin, account_views.PasswordResetView):
    turbo_stream_target = "password-reset-form"


password_reset = PasswordResetView.as_view()


class PasswordResetFromKeyView(
    TurboStreamFormMixin, account_views.PasswordResetFromKeyView
):
    turbo_stream_target = "password-reset-from-key-form"


password_reset_from_key = PasswordResetFromKeyView.as_view()
