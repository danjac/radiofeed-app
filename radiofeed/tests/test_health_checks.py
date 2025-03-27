import pytest
from health_check.exceptions import ServiceUnavailable

from radiofeed.health_checks import DatabaseHeartBeatHealthCheck, SimplePingHealthCheck


class TestSimplePingHealthCheck:
    def test_check_status(self):
        SimplePingHealthCheck().check_status()


class MockCursor:
    def __init__(self, return_value):
        self.return_value = return_value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, query):
        pass

    def fetchone(self):
        return self.return_value


class TestDatabaseHeartBeatHealthCheck:
    def test_check_status_ok(self, mocker):
        mocker.patch(
            "radiofeed.health_checks.connection.cursor",
            return_value=MockCursor((1,)),
        )
        DatabaseHeartBeatHealthCheck().check_status()

    def test_check_status_result_invalid(self, mocker):
        mocker.patch(
            "radiofeed.health_checks.connection.cursor",
            return_value=MockCursor(None),
        )
        with pytest.raises(ServiceUnavailable):
            DatabaseHeartBeatHealthCheck().check_status()

    def test_check_status_other_exception(self, mocker):
        mocker.patch(
            "radiofeed.health_checks.connection.cursor",
            side_effect=ValueError("invalid connection"),
        )
        with pytest.raises(ServiceUnavailable):
            DatabaseHeartBeatHealthCheck().check_status()
