# All auth views

# Third Party Libraries
from allauth.socialaccount import views as socialaccount_views

# RadioFeed
from radiofeed.common.turbo.mixins import TurboStreamFormMixin


class SignupView(TurboStreamFormMixin, socialaccount_views.SignupView):
    turbo_stream_target = "signup-form"
    turbo_stream_template = "socialaccount/_signup.html"


signup = SignupView.as_view()


class ConnectionsView(TurboStreamFormMixin, socialaccount_views.ConnectionsView):
    turbo_stream_target = "connections-form"
    turbo_stream_template = "socialaccount/_connections.html"


connections = ConnectionsView.as_view()
