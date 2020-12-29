# All auth views

# Third Party Libraries
from allauth.socialaccount import views as socialaccount_views
from turbo_response.mixins import TurboStreamFormMixin


class SignupView(TurboStreamFormMixin, socialaccount_views.SignupView):
    turbo_stream_target = "signup-form"


signup = SignupView.as_view()
