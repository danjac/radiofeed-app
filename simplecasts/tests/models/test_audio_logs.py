import pytest

from simplecasts.models import AudioLog
from simplecasts.tests.factories import AudioLogFactory


class TestAudioLogManager:
    @pytest.mark.django_db
    def test_search(self):
        audio_log1 = AudioLogFactory(
            episode__title="Learn Python Programming",
            episode__podcast__title="Tech Talks",
        )
        audio_log2 = AudioLogFactory(
            episode__title="Advanced Django Techniques",
            episode__podcast__title="Web Dev Weekly",
        )

        results = AudioLog.objects.search("Python")
        assert audio_log1 in results
        assert audio_log2 not in results


class TestAudioLogModel:
    @pytest.mark.parametrize(
        ("current_time", "duration", "expected"),
        [
            pytest.param(0, 0, 0, id="both zero"),
            pytest.param(0, 0, 0, id="current time zero"),
            pytest.param(60 * 60, 0, 0, id="duration zero"),
            pytest.param(60 * 60, 60 * 60, 100, id="both one hour"),
            pytest.param(60 * 30, 60 * 60, 50, id="current time half"),
            pytest.param(60 * 60, 30 * 60, 100, id="more than 100 percent"),
        ],
    )
    def test_percent_complete(self, current_time, duration, expected):
        audio_log = AudioLog(
            current_time=current_time,
            duration=duration,
        )
        assert audio_log.percent_complete == expected
