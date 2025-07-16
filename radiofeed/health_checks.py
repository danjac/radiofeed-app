from health_check.backends import BaseHealthCheckBackend


class SimplePingHealthCheck(BaseHealthCheckBackend):
    """Just checks service is alive."""

    critical_service = False

    def check_status(self):
        """Check service is alive, nothing more."""
