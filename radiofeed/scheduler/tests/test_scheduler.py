from radiofeed.scheduler import clear_sessions


class TestClearSessions:
    def test_run(self, mocker):
        mock_call_command = mocker.patch("radiofeed.scheduler.call_command")
        clear_sessions()
        mock_call_command.assert_called_once_with("clearsessions")
