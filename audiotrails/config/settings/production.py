from audiotrails.config.settings.base import *  # noqa
from audiotrails.config.settings.base import BASE_DIR
from audiotrails.config.settings.mixins.aws import *  # noqa
from audiotrails.config.settings.mixins.aws import (
    AWS_STATIC_CLOUDFRONT_DOMAIN,
    AWS_STATIC_LOCATION,
)
from audiotrails.config.settings.mixins.mailgun import *  # noqa
from audiotrails.config.settings.mixins.permissions import *  # noqa
from audiotrails.config.settings.mixins.secure import *  # noqa
from audiotrails.config.settings.mixins.sentry import *  # noqa

STATIC_URL = "https://" + AWS_STATIC_CLOUDFRONT_DOMAIN + "/" + AWS_STATIC_LOCATION + "/"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_FILE_STORAGE = "audiotrails.shared.storages.MediaStorage"

STATIC_ROOT = BASE_DIR / "staticfiles"

# https://github.com/jazzband/sorl-thumbnail#frequently-asked-questions

THUMBNAIL_FORCE_OVERWRITE = True
