from django.core.management import call_command


class TestClearCache:
    def test_clear_cache(self, mocker):
        mock_clear = mocker.patch("django.core.cache.cache.clear")
        call_command("clear_cache")
        mock_clear.assert_called_once()
