# Third Party Libraries
import pytest

# Local
from ..factories import EpisodeFactory
from ..templatetags.episodes import (
    duration_in_seconds,
    format_duration,
    get_player,
    is_playing,
)

pytestmark = pytest.mark.django_db


class TestIsPlaying:
    def test_is_playing_if_no_player(self, rf, episode):
        req = rf.get("/")
        req.session = {}
        assert not is_playing({"request": req}, episode)

    def test_is_playing_if_not_same_episode(self, rf, episode):
        req = rf.get("/")
        req.session = {"player": {"episode": EpisodeFactory().id}}
        assert not is_playing({"request": req}, episode)

    def test_is_playing_if_same_episode(self, rf, episode):
        req = rf.get("/")
        req.session = {"player": {"episode": episode.id}}
        assert is_playing({"request": req}, episode)


class TestGetPlayer:
    def test_get_player_if_none(self, rf, episode):
        req = rf.get("/")
        req.session = {}
        assert get_player({"request": req}) is None

    def test_get_player_if_episode_does_not_exist(self, rf):
        req = rf.get("/")
        req.session = {"player": {"episode": 12345, "current_time": 1000,}}
        assert get_player({"request": req}) is None

    def test_get_player_if_episode_exists(self, rf, episode):
        req = rf.get("/")
        req.session = {"player": {"episode": episode.id, "current_time": 1000,}}
        assert get_player({"request": req}) == {
            "episode": episode,
            "current_time": 1000,
        }


class TestDurationInSeconds:
    def test_duration_in_seconds_if_empty(self):
        assert duration_in_seconds(None) == 0
        assert duration_in_seconds("") == 0

    def test_duration_in_seconds_if_non_numeric(self):
        assert duration_in_seconds("NaN") == 0

    def test_duration_in_seconds_if_seconds_only(self):
        assert duration_in_seconds("60") == 60

    def test_duration_in_seconds_if_minutes_and_seconds(self):
        assert duration_in_seconds("2:30") == 150

    def test_duration_in_seconds_if_hours_minutes_and_seconds(self):
        assert duration_in_seconds("2:30:30") == 9030


class TestFormatDuration:
    def test_format_duration_if_empty(self):
        assert format_duration(None) == ""
        assert format_duration("0") == ""
        assert format_duration("") == ""

    def test_format_duration_if_less_than_one_minute(self):
        assert format_duration("30") == "<1min"

    def test_format_duration_if_less_than_one_hour(self):
        assert format_duration("2400") == "40min"

    def test_format_duration_if_more_than_one_hour(self):
        assert format_duration("9000") == "2h 30min"
