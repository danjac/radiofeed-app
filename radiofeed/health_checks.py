from health_check.backends import HealthCheck


class SimplePingHealthCheck(HealthCheck):
    """Just checks service is alive."""

    critical_service = False

    def check_status(self):
        """Check service is alive, nothing more."""
