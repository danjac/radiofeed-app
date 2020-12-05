# Local
from .base import *  # noqa
from .mixins.aws import *  # noqa
from .mixins.mailgun import *  # noqa
from .mixins.secure import *  # noqa
# from .mixins.sentry import *  # noqa

# Required for Heroku SSL
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
