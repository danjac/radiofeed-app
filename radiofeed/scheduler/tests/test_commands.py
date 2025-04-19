from django.core.management import call_command


class TestScheduler:
    def test_command(self, mocker):
        mock_start = mocker.patch("radiofeed.scheduler.scheduler.start")
        call_command("scheduler")
        mock_start.assert_called_once()
