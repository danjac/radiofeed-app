import pathlib

import pytest
from django.core.management import call_command

from radiofeed.podcasts.models import Podcast


class TestImportOpml:
    patched = "radiofeed.feedparser.opml_parser.parse_opml"

    @pytest.fixture
    def filename(self):
        return pathlib.Path(__file__).parent / "mocks" / "feeds.opml"

    @pytest.mark.django_db
    def test_command(self, mocker, filename):
        patched = mocker.patch(self.patched, return_value=iter(["https://example.com"]))
        call_command("import_opml", filename)
        assert Podcast.objects.count() == 1
        podcast = Podcast.objects.first()
        assert podcast is not None
        patched.assert_called()

    @pytest.mark.django_db
    def test_empty(self, mocker, filename):
        patched = mocker.patch(self.patched, return_value=iter([]))
        call_command("import_opml", filename)
        assert Podcast.objects.count() == 0
        patched.assert_called()


class TestExportFeeds:
    @pytest.mark.django_db
    def test_ok(self, podcast):
        call_command("export_opml", "-")
