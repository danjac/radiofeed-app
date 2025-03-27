from django.db import connection
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable


class SimplePingHealthCheck(BaseHealthCheckBackend):
    """Just checks service is alive."""

    critical_service = False

    def check_status(self):
        """Check service is alive, nothing more."""


class DatabaseHeartBeatHealthCheck(BaseHealthCheckBackend):
    """Health check that runs a simple SELECT 1; query to test if the database connection is alive.

    NOTE: this is available in latest version of health_check but not in release. Remove when upgrading.
    """

    def check_status(self):
        """Check database connection is alive."""
        try:
            result = None
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                result = cursor.fetchone()

            if result != (1,):
                raise ServiceUnavailable(
                    "Health Check query did not return the expected result."
                )
        except Exception as e:
            raise ServiceUnavailable(f"Database health check failed: {e}") from e
