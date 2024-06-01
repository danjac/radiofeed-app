from django.core.checks import Tags, register

from listenwave.checks import check_secure_admin_url

register(check_secure_admin_url, Tags.security, deploy=True)
