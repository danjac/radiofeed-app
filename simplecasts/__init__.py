from django.core.checks import Tags, register
from health_check.plugins import plugin_dir

from simplecasts.checks import check_secure_admin_url
from simplecasts.health_checks import SimplePingHealthCheck

# register custom Django system checks
register(check_secure_admin_url, Tags.security, deploy=True)


# register custom health checks
plugin_dir.register(SimplePingHealthCheck)
