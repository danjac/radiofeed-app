from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from jcasts.users.models import User  # pragma: no cover
else:
    User = get_user_model()
