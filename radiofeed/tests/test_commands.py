import pytest
from click.exceptions import Exit
from django.core.management import call_command


class TestClearCache:
    def test_command(self, mocker):
        mock_confirm = mocker.patch("djclick.confirm", return_value=True)
        call_command("clear_cache")
        mock_confirm.assert_called_once_with(
            "Are you sure you want to clear the cache?", abort=True
        )

    def test_command_no_input(self, mocker):
        mock_confirm = mocker.patch("djclick.confirm", return_value=True)
        call_command("clear_cache", no_input=True)
        mock_confirm.assert_not_called()

    def test_invalid_cache_name(self):
        with pytest.raises(Exit):
            call_command(
                "clear_cache", cache_names=["invalid_cache_name"], no_input=True
            )
