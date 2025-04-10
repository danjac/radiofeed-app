from radiofeed.jobs import clear_sessions


class TestClearSessions:
    def test_clear_sessions(self, mocker):
        # Mock the function to be tested
        mock_clear_sessions = mocker.patch("radiofeed.jobs.call_command")

        # Call the function
        clear_sessions()

        # Assert that the function was called
        mock_clear_sessions.assert_called_once()
