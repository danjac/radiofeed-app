from radiofeed.health_checks import SimplePingHealthCheck


class TestSimplePingHealthCheck:
    def test_check_status(self):
        SimplePingHealthCheck().check_status()
