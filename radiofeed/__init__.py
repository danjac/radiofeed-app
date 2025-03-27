from django.core.checks import Tags, register
from health_check.plugins import plugin_dir

from radiofeed.checks import check_secure_admin_url
from radiofeed.health_checks import DatabaseHeartBeatHealthCheck, SimplePingHealthCheck

# register custom Django system checks
register(check_secure_admin_url, Tags.security, deploy=True)


# register custom health checks
plugin_dir.register(SimplePingHealthCheck)
plugin_dir.register(DatabaseHeartBeatHealthCheck)
