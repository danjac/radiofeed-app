from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from django.contrib.auth.models import User
else:
    User = get_user_model()
