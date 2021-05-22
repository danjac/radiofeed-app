from .base import *  # noqa
from .base import BASE_DIR
from .mixins.aws import *  # noqa
from .mixins.aws import AWS_STATIC_CLOUDFRONT_DOMAIN, AWS_STATIC_LOCATION
from .mixins.mailgun import *  # noqa
from .mixins.permissions import *  # noqa
from .mixins.secure import *  # noqa
from .mixins.sentry import *  # noqa

STATIC_URL = "https://" + AWS_STATIC_CLOUDFRONT_DOMAIN + "/" + AWS_STATIC_LOCATION + "/"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_FILE_STORAGE = "audiotrails.shared.storages.MediaStorage"

STATIC_ROOT = BASE_DIR / "staticfiles"

# https://github.com/jazzband/sorl-thumbnail#frequently-asked-questions

THUMBNAIL_FORCE_OVERWRITE = True
