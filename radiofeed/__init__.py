from django.core.checks import Tags, register

from radiofeed.checks import check_secure_admin_url

# register custom Django system checks
register(check_secure_admin_url, Tags.security, deploy=True)
