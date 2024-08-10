from django.core.checks import Tags, register

from radiofeed.checks import check_secure_admin_url

# add custom checks

register(check_secure_admin_url, Tags.security, deploy=True)
