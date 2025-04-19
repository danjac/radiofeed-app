from django.core.management import call_command


class TestScheduler:
    def test_command(self, mocker):
        mock_start = mocker.patch("radiofeed.scheduler.scheduler.start")
        call_command("scheduler")
        mock_start.assert_called_once()

    def test_shutdown(self, mocker):
        mock_start = mocker.patch(
            "radiofeed.scheduler.scheduler.start",
            side_effect=KeyboardInterrupt,
        )
        mock_shutdown = mocker.patch("radiofeed.scheduler.scheduler.shutdown")
        call_command("scheduler")
        mock_start.assert_called_once()
        mock_shutdown.assert_called_once()
