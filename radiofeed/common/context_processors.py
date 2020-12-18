# Django
from django.conf import settings


def google_tracking_id(request):
    return {"google_tracking_id": getattr(settings, "GOOGLE_TRACKING_ID", None)}
