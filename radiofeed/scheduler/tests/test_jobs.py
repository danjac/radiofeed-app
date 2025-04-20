import pytest
from django.utils import timezone
from django_apscheduler.models import DjangoJobExecution

from radiofeed.scheduler.jobs import clear_sessions, delete_old_job_executions
from radiofeed.scheduler.tests.factories import DjangoJobExecutionFactory


class TestClearSessions:
    def test_run(self, mocker):
        mock_call_command = mocker.patch("radiofeed.scheduler.jobs.call_command")
        clear_sessions()
        mock_call_command.assert_called_once_with("clearsessions")


class TestDeleteOldJobExecutions:
    @pytest.mark.django_db
    def test_not_old_enough(self):
        DjangoJobExecutionFactory(run_time=timezone.now() - timezone.timedelta(hours=1))
        delete_old_job_executions()
        assert DjangoJobExecution.objects.exists() is True

    @pytest.mark.django_db
    def test_old_enough(self):
        DjangoJobExecutionFactory(run_time=timezone.now() - timezone.timedelta(days=2))
        delete_old_job_executions()
        assert DjangoJobExecution.objects.exists() is False
